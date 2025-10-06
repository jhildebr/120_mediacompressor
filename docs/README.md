# Documentation Index

Complete documentation for the Azure Media Compression System.

---

## 🚀 Getting Started

**New to this project?** Start here:

1. **[../README.md](../README.md)** - Main documentation with quick start guide
2. **[API.md](./API.md)** - API reference for frontend integration
3. **[FILE_STRUCTURE.md](./FILE_STRUCTURE.md)** - Understanding the codebase

---

## 📖 Documentation Files

### Core Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[README.md](../README.md)** | System overview, quick start, examples | Everyone |
| **[API.md](./API.md)** | Complete API reference | Frontend developers |
| **[FILE_STRUCTURE.md](./FILE_STRUCTURE.md)** | Repository structure guide | Backend developers |

### Setup & Operations

| Document | Purpose | Audience |
|----------|---------|----------|
| **[APP_SERVICE_B2_MIGRATION.md](../APP_SERVICE_B2_MIGRATION.md)** | Migration from Functions EP1 | DevOps, System admins |
| **[AZURE_STORAGE_AUTH.md](../AZURE_STORAGE_AUTH.md)** | Storage authentication setup | DevOps, Developers |

### Reference

| Document | Purpose | Audience |
|----------|---------|----------|
| **[DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md)** | Documentation consolidation details | Maintainers |

---

## 🎯 Find What You Need

### "I want to..."

| Goal | Document |
|------|----------|
| Deploy the application | [README.md § Quick Start](../README.md#-quick-start) |
| Integrate with my frontend | [README.md § Frontend Integration](../README.md#-frontend-integration) |
| Understand the API | [API.md](./API.md) |
| Troubleshoot an issue | [README.md § Troubleshooting](../README.md#-troubleshooting) |
| Understand the costs | [README.md § Cost Breakdown](../README.md#-cost-breakdown) |
| Migrate from EP1 | [APP_SERVICE_B2_MIGRATION.md](../APP_SERVICE_B2_MIGRATION.md) |
| Set up authentication | [AZURE_STORAGE_AUTH.md](../AZURE_STORAGE_AUTH.md) |
| Navigate the codebase | [FILE_STRUCTURE.md](./FILE_STRUCTURE.md) |

### "I'm a..."

**Frontend Developer:**
1. [README.md § Frontend Integration](../README.md#-frontend-integration)
2. [API.md](./API.md)
3. [README.md § Supported Formats](../README.md#-supported-formats)

**Backend Developer:**
1. [README.md](../README.md)
2. [FILE_STRUCTURE.md](./FILE_STRUCTURE.md)
3. [README.md § Development](../README.md#-development)

**DevOps Engineer:**
1. [README.md § Quick Start](../README.md#-quick-start)
2. [APP_SERVICE_B2_MIGRATION.md](../APP_SERVICE_B2_MIGRATION.md)
3. [AZURE_STORAGE_AUTH.md](../AZURE_STORAGE_AUTH.md)

**System Administrator:**
1. [README.md § Monitoring](../README.md#-monitoring)
2. [README.md § Configuration](../README.md#-configuration)
3. [README.md § Troubleshooting](../README.md#-troubleshooting)

---

## 📂 Documentation Structure

```
docs/
├── README.md                       # This index file
├── API.md                          # Complete API reference
├── FILE_STRUCTURE.md               # Repository structure guide
├── DOCUMENTATION_SUMMARY.md        # Consolidation summary
└── archived/                       # Legacy documentation
    ├── README.md                   # Archive index
    ├── PROJECT_OVERVIEW.md
    ├── AZURE_MEDIA_COMPRESSION_SYSTEM.md
    ├── DEPLOYMENT_GUIDE.md
    ├── IMPLEMENTATION_SUMMARY.md
    └── TESTING.md

Root level:
├── README.md                       # Main entry point
├── APP_SERVICE_B2_MIGRATION.md     # Migration guide
└── AZURE_STORAGE_AUTH.md           # Auth setup guide
```

---

## 🔄 Documentation Updates

### Last Major Update
**Date:** 2025-10-05
**Changes:** Consolidated documentation to reflect App Service B2 architecture

**What Changed:**
- Rewrote README.md for App Service B2
- Created comprehensive API.md
- Added FILE_STRUCTURE.md
- Archived outdated Functions EP1 documentation
- Updated test-flow.sh

See [DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md) for full details.

---

## 📋 Quick Reference

### Key URLs

| Environment | URL |
|-------------|-----|
| Production | `https://mediaprocessor-b2.azurewebsites.net` |
| Health Check | `https://mediaprocessor-b2.azurewebsites.net/api/health` |
| API Docs | This folder |

### Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/deploy-app-service-b2.sh` | Deploy to production |
| `test-flow.sh` | End-to-end test |
| `scripts/cleanup-unused-resources.sh` | Clean up old resources |

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/version` | GET | Version info |
| `/api/process` | POST | Process uploaded file |
| `/api/status` | GET | Query job status (auth required) |

---

## 💡 Tips

### For Documentation Maintainers

**When updating docs:**
1. Update version/date stamps
2. Check all internal links still work
3. Update code examples if API changed
4. Keep README.md and API.md in sync
5. Archive old versions, don't delete

**File naming:**
- Use `SCREAMING_CASE.md` for important top-level docs
- Use `Title_Case.md` for reference/guide docs
- Keep filenames descriptive and unique

### For Readers

**Can't find something?**
1. Check the main [README.md](../README.md) first
2. Use browser search (Cmd/Ctrl+F) within docs
3. Check [FILE_STRUCTURE.md](./FILE_STRUCTURE.md) for file locations
4. Look in [archived/](./archived/) for legacy information

**Something outdated?**
- Documentation last updated: 2025-10-05
- If Azure pricing/features changed, please update

---

## ✅ Documentation Quality Checklist

All current documentation includes:
- ✅ Clear purpose statement
- ✅ Target audience identified
- ✅ Up-to-date examples
- ✅ Working code snippets
- ✅ Current URLs and endpoints
- ✅ Version and date stamps
- ✅ Internal links verified

---

**Last Updated:** 2025-10-05
**Documentation Version:** 1.0 (App Service B2)
**Status:** ✅ Current and Accurate
