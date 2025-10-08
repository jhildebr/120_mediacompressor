# Angular Integration Guide - Interim /api/upload Endpoint

**Branch:** `feature/interim-upload-endpoint`
**Endpoint:** `https://mediaprocessor-b2.azurewebsites.net/api/upload`
**Status:** ✅ DEPLOYED AND TESTED

---

## Overview

This guide shows how to integrate the interim `/api/upload` endpoint into the SIMPI Angular frontend. This endpoint accepts direct file uploads and returns compressed files.

**⚠️ Note:** This is a temporary testing solution. For production, we'll migrate to Phase 2 (SIMPI storage integration).

---

## Quick Start

### 1. Add Service to Angular Project

**File:** `projects/simpi-frontend-common/src/lib/services/compression/media-compression.service.ts`

```typescript
import { Injectable, Inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { COMMON_CONFIG, SimpiCommonConfig } from '../../simpi-common-config';

export interface CompressionResult {
  compressedFile: Blob;
  originalSize: number;
  compressedSize: number;
  compressionRatio: number;
  processingTime: number;
  fileName: string;
}

@Injectable({ providedIn: 'root' })
export class MediaCompressionService {

  private readonly compressorUrl = 'https://mediaprocessor-b2.azurewebsites.net';

  constructor(
    @Inject(COMMON_CONFIG) private config: SimpiCommonConfig,
    private http: HttpClient
  ) {}

  /**
   * Compresses media file (image or video) using Azure compression service.
   * @param file Original file to compress
   * @returns Observable<CompressionResult>
   */
  public compressMedia(file: File): Observable<CompressionResult> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post(
      `${this.compressorUrl}/api/upload`,
      formData,
      {
        responseType: 'blob',
        observe: 'response',
      }
    ).pipe(
      map(response => {
        const compressedBlob = response.body;
        const headers = response.headers;

        return {
          compressedFile: compressedBlob,
          originalSize: parseInt(headers.get('X-Original-Size') || '0', 10),
          compressedSize: parseInt(headers.get('X-Compressed-Size') || '0', 10),
          compressionRatio: parseFloat(headers.get('X-Compression-Ratio') || '1'),
          processingTime: parseFloat(headers.get('X-Processing-Time') || '0'),
          fileName: this.getCompressedFileName(file.name),
        };
      }),
      tap(result => {
        console.log('Compression complete:', {
          original: `${(result.originalSize / 1024 / 1024).toFixed(2)} MB`,
          compressed: `${(result.compressedSize / 1024 / 1024).toFixed(2)} MB`,
          saved: `${((1 - result.compressionRatio) * 100).toFixed(1)}%`,
          time: `${result.processingTime.toFixed(2)}s`,
        });
      })
    );
  }

  /**
   * Checks if file is a media file (image or video).
   */
  public isMediaFile(file: File): boolean {
    return file.type.startsWith('image/') || file.type.startsWith('video/');
  }

  /**
   * Gets the compressed file name (changes extension to .mp4 or .webp).
   */
  private getCompressedFileName(originalName: string): string {
    const nameWithoutExt = originalName.split('.').slice(0, -1).join('.');
    const ext = originalName.split('.').pop()?.toLowerCase();

    // Videos output as .mp4
    if (ext && ['mp4', 'mov', 'avi', 'webm', 'flv', 'wmv'].includes(ext)) {
      return `${nameWithoutExt}.mp4`;
    }

    // Images output as .webp
    if (ext && ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) {
      return `${nameWithoutExt}.webp`;
    }

    return originalName;
  }
}
```

---

## Integration into Existing Upload Service

### Update `step-media-upload.service.ts`

**File:** `projects/simpi-frontend-common/src/lib/services/steps/step-media-upload.service.ts`

```typescript
import { MediaCompressionService, CompressionResult } from '../compression/media-compression.service';

// Add to constructor
constructor(
  private stepService: StepService,
  private imageService: ImageService,
  private compressionService: MediaCompressionService  // ADD THIS
) {}

// Modify uploadStepMedia method
public async uploadStepMedia(fileToUpload: File): Promise<UploadStepMediaResult> {
  const mediaType: string = this.detectMediaType(fileToUpload);
  if (!mediaType) {
    this.logError('uploadStepMedia', `File type not supported: '${fileToUpload.type}'.`);
    return Promise.reject(new Error(`Invalid MediaType: '${fileToUpload.type}'`));
  }

  const result: UploadStepMediaResult = {
    mediaType: mediaType,
    success: false,
  };

  try {
    // NEW: Compress media first
    this.logDebug('uploadStepMedia', 'Compressing media...');

    const compressionResult: CompressionResult = await this.compressionService
      .compressMedia(fileToUpload)
      .toPromise();

    this.logDebug('uploadStepMedia',
      `Compression complete. Size reduced by ${((1 - compressionResult.compressionRatio) * 100).toFixed(1)}%`
    );

    // Convert compressed blob to File for SIMPI backend
    const compressedFile = new File(
      [compressionResult.compressedFile],
      compressionResult.fileName,
      { type: compressionResult.compressedFile.type }
    );

    // Continue with existing upload logic using compressed file
    if (mediaType === STEP_MEDIA_TYPE_VIDEO) {
      this.logDebug('uploadStepMedia', 'Generating thumbnail from compressed video...');
      const thumbnail: File = await this.imageService.getThumbnailFromVideo(
        compressedFile,
        new Vector2(240, 384)
      );

      this.logDebug('uploadStepMedia', 'Uploading thumbnail...');
      const uploadThumbnailResponse = await this.stepService
        .uploadStepThumbnail(thumbnail)
        .toPromise();

      if (!this.isUploadResponseOk(uploadThumbnailResponse, 'uploadStepMedia', 'thumbnail')) {
        return result;
      }

      result.thumbnailId = uploadThumbnailResponse.body.imageId;
      result.thumbnailUrl = this.stepService.getStepImageUrl(uploadThumbnailResponse.body.imageId);

      this.logDebug('uploadStepMedia', 'Uploading compressed video...');
      const uploadVideoResponse = await this.stepService
        .uploadStepVideo(compressedFile)
        .toPromise();

      if (!this.isUploadResponseOk(uploadVideoResponse, 'uploadStepMedia', 'video')) {
        return result;
      }

      result.videoId = uploadVideoResponse.body.videoId;
      result.videoUrl = this.stepService.getStepVideoUrl(uploadVideoResponse.body.videoId);
      result.success = true;

    } else if (mediaType === STEP_MEDIA_TYPE_IMAGE) {
      this.logDebug('uploadStepMedia', 'Uploading compressed image...');
      const uploadStepImageResponse = await this.stepService
        .uploadStepImage(compressedFile)
        .toPromise();

      if (!this.isUploadResponseOk(uploadStepImageResponse, 'uploadStepMedia', 'image')) {
        return result;
      }

      result.thumbnailId = uploadStepImageResponse.body.imageId;
      result.thumbnailUrl = this.stepService.getStepImageUrl(uploadStepImageResponse.body.imageId);
      result.videoId = null;
      result.videoUrl = null;
      result.success = true;
    }

    this.latestUploadStepMediaResult = result;
    return result;

  } catch (error) {
    this.logError('uploadStepMedia', `Error uploading media: ${error}.`);
    this.latestUploadStepMediaResult = result;
    return Promise.reject(error);
  }
}
```

---

## UI Integration Example

### Add Progress Indicator

**Component:** `upload-img-modal.component.ts`

```typescript
export class UploadImgModalComponent {
  public compressionProgress: {
    stage: 'idle' | 'compressing' | 'uploading' | 'complete';
    message: string;
  } = {
    stage: 'idle',
    message: '',
  };

  private uploadPicture(file: any): void {
    this.compressionProgress = {
      stage: 'compressing',
      message: 'Compressing image...',
    };

    this.uploadImgModalService.uploadImageToServer(this.imageType, file)
      .subscribe(
        uploadedImageId => {
          this.compressionProgress = {
            stage: 'complete',
            message: 'Upload complete',
          };
          this.uploadedImageId = uploadedImageId;
          this.pictureUrl = this.uploadImgModalService.getImageUrlFromImageId(
            uploadedImageId,
            this.imageType
          );
          this.processing = false;
        },
        error => {
          this.compressionProgress = { stage: 'idle', message: '' };
          console.error('Upload failed:', error);
          this.processing = false;
        }
      );
  }
}
```

**Template:** `upload-img-modal.component.html`

```html
<div *ngIf="compressionProgress.stage !== 'idle'" class="compression-progress">
  <div class="alert alert-info">
    <i class="fa fa-spin fa-spinner"></i>
    {{ compressionProgress.message }}
  </div>
</div>
```

---

## Testing the Integration

### Manual Testing Steps

1. **Test Image Upload** (PNG/JPG)
```typescript
// In browser console or test component:
const input = document.querySelector('input[type="file"]');
input.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const service = // inject MediaCompressionService

  service.compressMedia(file).subscribe(
    result => console.log('Success:', result),
    error => console.error('Error:', error)
  );
});
```

2. **Test Video Upload** (MP4/MOV)
```typescript
// Same as above but with video file
```

3. **Verify Results**
- Check browser Network tab for `/api/upload` request
- Verify response headers contain compression metrics
- Confirm compressed file is smaller than original
- Test that compressed file plays/displays correctly

---

## Error Handling

```typescript
public compressMedia(file: File): Observable<CompressionResult> {
  return this.http.post(/* ... */).pipe(
    catchError(error => {
      if (error.status === 400) {
        console.error('Invalid file type or size');
      } else if (error.status === 500) {
        console.error('Compression failed on server');
      }
      return throwError(() => new Error('Compression failed'));
    })
  );
}
```

---

## Expected Results

### Image Compression (PNG → WebP)
- **Input:** 5MB PNG
- **Output:** ~1.5MB WebP (70% reduction)
- **Time:** 1-2 seconds

### Video Compression (MOV → MP4)
- **Input:** 20MB MOV (1080p)
- **Output:** Depends on duration (VBR @ 1.2 Mbps target)
- **Bitrate:** 1.2 Mbps target, 2 Mbps max
- **Resolution:** Max 1920x1080 (aspect ratio preserved)
- **Time:** 5-10 seconds (varies by duration)

---

## Troubleshooting

### Issue: "No file provided" Error
**Solution:** Ensure FormData key is exactly `'file'`:
```typescript
formData.append('file', file);  // Correct
formData.append('media', file);  // Wrong
```

### Issue: Timeout on Large Files
**Solution:** Videos > 50MB may timeout. Current limit is 100MB.

### Issue: "Unsupported file type"
**Solution:** Check file extension matches allowed types:
- Videos: mp4, mov, avi, webm, flv, wmv
- Images: jpg, jpeg, png, gif, bmp, webp

---

## Next Steps: Production Migration

Once testing is complete, we'll migrate to the production architecture:

1. **Deploy compressor to SIMPI subscription**
2. **Use SIMPI storage account**
3. **Update to Phase 2 flow:**
   - Frontend uploads to SIMPI storage
   - Call `/api/process` with blob name
   - No file download needed
   - More efficient

---

## Support

**Issues?** Check logs at:
```bash
az webapp log tail \
  --name mediaprocessor-b2 \
  --resource-group rg-11-video-compressor-az-function
```

**Questions?** The endpoint is temporary - focus on testing compression quality/speed, not long-term integration.
