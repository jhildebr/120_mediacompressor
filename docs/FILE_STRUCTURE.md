# Project File Structure

Complete guide to the repository structure and what each file does.

---

## 📁 Root Directory

### Core Application Files

| File | Purpose | Status |
|------|---------|--------|
| `function_app.py` | Main application entry point (Azure Functions SDK) | ✅ Active |
| `Dockerfile` | Container image definition (Python 3.11 + FFmpeg) | ✅ Active |
| `requirements.txt` | Python dependencies | ✅ Active |
| `host.json` | Azure Functions host configuration | ✅ Active |
| `.dockerignore` | Files to exclude from Docker build | ✅ Active |
| `.gitignore` | Files to exclude from git | ✅ Active |

### Documentation

| File | Purpose | Status |
|------|---------|--------|
| `README.md` | **Main documentation** - start here! | ✅ Active |
| `APP_SERVICE_B2_MIGRATION.md` | Migration guide from Functions EP1 | ✅ Active |
| `AZURE_STORAGE_AUTH.md` | Storage authentication setup | ✅ Active |

### Testing

| File | Purpose | Status |
|------|---------|--------|
| `test-flow.sh` | End-to-end test script | ✅ Active |

---

## 📁 processing/

Media processing logic (FFmpeg, Pillow).

| File | Purpose | Key Functions |
|------|---------|---------------|
| `video.py` | Video compression using FFmpeg | `process_video()` |
| `image.py` | Image compression using Pillow | `process_image()` |

**Technologies:**
- FFmpeg (H.264 encoding, VBR @ 1.2 Mbps target)
- Pillow (PNG/JPG optimization)

---

## 📁 integrations/

External service integrations and infrastructure.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `tracking.py` | Job tracking via Azure Table Storage | `create_job_record()`, `update_job_status()`, `get_job_status()` |
| `auth.py` | API key authentication | `require_auth()`, `validate_api_key()` |
| `database.py` | SIMPI API integration | `update_database()` |
| `notifications.py` | Webhook/SignalR notifications | `send_completion_notification()` |
| `errors.py` | Error handling and retries | `handle_processing_error()` |

**Azure Services Used:**
- Azure Table Storage (`processingjobs` table)
- Azure Blob Storage (SAS token generation)
- External REST APIs

---

## 📁 config/

Configuration files.

| File | Purpose |
|------|---------|
| `compression_config.py` | Video/image compression settings (bitrate, quality, presets) |

---

## 📁 scripts/

Deployment and management scripts.

### Active Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `deploy-app-service-b2.sh` | **Deploy to App Service B2** (current) | Main deployment script |
| `cleanup-unused-resources.sh` | Delete unused queues and containers | After EP1 deletion |

### Legacy Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `build-in-azure.sh` | Deploy to Functions EP1 | ⚠️ Legacy (still works for EP1) |
| `build-and-deploy.sh` | Old deployment script | ⚠️ Deprecated |
| `setup-container-registry.sh` | ACR setup | ✅ Active (one-time setup) |
| `set-env-vars.sh` | Environment variable setup | ⚠️ Legacy |
| `fix-function-runtime.sh` | Runtime fix script | ⚠️ Legacy |
| `deploy-infrastructure.sh` | Infrastructure deployment | ⚠️ Legacy |

---

## 📁 docs/

Documentation files.

### Active Documentation

| File | Purpose |
|------|---------|
| `API.md` | Complete API reference |
| `FILE_STRUCTURE.md` | This file - repository structure |

### Subdirectories

| Directory | Purpose |
|-----------|---------|
| `docs/archived/` | Outdated documentation from Functions EP1 era |
| `docs/api/` | Legacy API documentation (OpenAPI specs) |

---

## 📁 media-uploader/

Next.js web application for file uploads (optional frontend).

### Key Files

| File/Directory | Purpose |
|----------------|---------|
| `src/app/page.tsx` | Main upload page |
| `src/app/api/upload/route.ts` | Upload endpoint |
| `src/app/api/status/route.ts` | Status checking endpoint |
| `src/components/FileUpload.tsx` | Upload UI component |
| `src/lib/azure-storage.ts` | Azure Storage client |

**Technologies:**
- Next.js 14 (App Router)
- TypeScript
- Azure Storage SDK
- Tailwind CSS

---

## 📊 Quick Reference

### "I want to..."

| Task | File to Check |
|------|---------------|
| Deploy the application | `scripts/deploy-app-service-b2.sh` |
| Understand the API | `docs/API.md` |
| Add new compression logic | `processing/video.py` or `processing/image.py` |
| Change compression settings | `config/compression_config.py` |
| Update job tracking | `integrations/tracking.py` |
| Test the system | `test-flow.sh` |
| See deployment logs | Azure Portal or `az webapp log tail` |

### "What does X do?"

| Component | File | Purpose |
|-----------|------|---------|
| `/api/process` | `function_app.py:226-324` | Main processing endpoint |
| `/api/status` | `function_app.py:272-347` | Status query endpoint |
| Job tracking | `integrations/tracking.py` | Azure Table Storage integration |
| Cleanup worker | `function_app.py:328-402` | Background thread deletes old files |

---

## 🗑️ Archived Files

Located in `docs/archived/`:

- `PROJECT_OVERVIEW.md` - Original overview (Functions-based)
- `AZURE_MEDIA_COMPRESSION_SYSTEM.md` - Original documentation (queue-based)
- `DEPLOYMENT_GUIDE.md` - Legacy deployment guide
- `IMPLEMENTATION_SUMMARY.md` - Original implementation notes
- `TESTING.md` - Legacy testing documentation

**Why archived:** System migrated from Functions EP1 (blob triggers + queues) to App Service B2 (direct HTTP).

---

## 📏 Naming Conventions

### Files
- Python: `snake_case.py`
- TypeScript: `PascalCase.tsx` or `camelCase.ts`
- Scripts: `kebab-case.sh`
- Docs: `SCREAMING_SNAKE_CASE.md` or `Title_Case.md`

### Blob Names
- Upload: `upload-{timestamp}.{ext}` (e.g., `upload-1759645846.png`)
- Processed: `processed-{timestamp}.{ext}` (e.g., `processed-1759645846.png`)

### Azure Resources
- App Service: `mediaprocessor-b2`
- Storage Account: `mediablobazfct`
- Container Registry: `mediacompressorregistry`
- Resource Group: `rg-11-video-compressor-az-function`

---

## 🔄 Migration History

| Date | Change | Files Affected |
|------|--------|----------------|
| 2025-10-05 | Migrated to App Service B2 | All deployment scripts, documentation |
| 2025-10-05 | Removed queue processing | `function_app.py` (removed queue trigger) |
| 2025-10-05 | Added direct HTTP processing | `function_app.py` (added `/api/process`) |
| 2025-10-05 | Added background cleanup worker | `function_app.py` (threading-based) |

---

**Last Updated:** 2025-10-05
**Current Platform:** Azure App Service B2
**Status:** ✅ Production Ready
