# Azure Storage Authentication - Fix Warnings

## The Warning Message

```
WARNING: There are no credentials provided in your command and environment...
It is recommended to provide --connection-string, --account-key or --sas-token...
```

**What it means:** Azure CLI automatically looks up your storage account key, but warns you could provide it explicitly.

**Impact:** ⚠️ Warning only - commands still work perfectly

## Solutions

### Option 1: Use Azure AD (Recommended) ✅

**What we changed:**
```bash
# Before
--auth-mode key

# After
--auth-mode login
```

**Benefits:**
- ✅ No warnings
- ✅ More secure (uses your Azure login, not storage keys)
- ✅ Better audit trail (who did what)
- ✅ Works with RBAC permissions

**Requirements:**
- You must be logged in: `az login`
- You need "Storage Blob Data Contributor" role on storage account

**Verify you have access:**
```bash
# Check your current login
az account show

# Test storage access
az storage blob list \
  --account-name mediablobazfct \
  --container-name uploads \
  --auth-mode login
```

**If you get permission denied:**
```bash
# Grant yourself Storage Blob Data Contributor role
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee $(az account show --query user.name -o tsv) \
  --scope /subscriptions/$(az account show --query id -o tsv)/resourceGroups/rg-11-video-compressor-az-function/providers/Microsoft.Storage/storageAccounts/mediablobazfct
```

### Option 2: Environment Variables (Alternative)

Set storage credentials once in your shell:

```bash
# Get connection string
export AZURE_STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name mediablobazfct \
  --resource-group rg-11-video-compressor-az-function \
  --query connectionString -o tsv)

# Now commands don't need --auth-mode at all
az storage blob upload \
  --account-name mediablobazfct \
  --container-name uploads \
  --file test.png \
  --name upload-test.png
  # No warnings!
```

**Add to your shell profile** (~/.zshrc or ~/.bashrc):
```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=mediablobazfct;AccountKey=...;"
```

### Option 3: Ignore It (Simplest)

**Just live with the warnings:**
- ✅ Everything works
- ✅ No configuration needed
- ❌ Warnings clutter output

To hide warnings only:
```bash
az storage blob upload ... --auth-mode key 2>&1 | grep -v WARNING
```

## What We Updated

**Files changed to use `--auth-mode login`:**
1. ✅ `scripts/cleanup-unused-resources.sh`
2. ✅ `test-flow.sh`

**Files that still have warnings** (if you use them directly):
- Any manual `az storage` commands you run

## Comparison

| Method | Warnings | Security | Setup |
|--------|----------|----------|-------|
| `--auth-mode login` | ✅ None | ✅ Best (Azure AD) | 1-time role assignment |
| Environment variable | ✅ None | ⚠️ Key in env | Export connection string |
| `--auth-mode key` (auto) | ❌ Yes | ✅ OK (auto lookup) | None |

## Testing

Test that warnings are gone:

```bash
# Run cleanup script
./scripts/cleanup-unused-resources.sh

# Should see:
# ✅ No credential warnings
# ✅ Clean output
```

## Troubleshooting

### "You do not have the required permissions"

**Solution:** Grant yourself the role:
```bash
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee $(az account show --query user.name -o tsv) \
  --scope /subscriptions/$(az account show --query id -o tsv)/resourceGroups/rg-11-video-compressor-az-function/providers/Microsoft.Storage/storageAccounts/mediablobazfct
```

Wait 1-2 minutes for permissions to propagate.

### "Authentication failed"

**Solution:** Login again:
```bash
az login
az account set --subscription <your-subscription-id>
```

### Still seeing warnings

Check you're using the updated scripts:
```bash
grep "auth-mode login" scripts/cleanup-unused-resources.sh
# Should show: --auth-mode login
```

## Summary

**Recommended approach:** Use `--auth-mode login` (already done in scripts)

**To enable:**
1. Login: `az login`
2. Grant role (one-time):
   ```bash
   az role assignment create \
     --role "Storage Blob Data Contributor" \
     --assignee $(az account show --query user.name -o tsv) \
     --scope /subscriptions/$(az account show --query id -o tsv)/resourceGroups/rg-11-video-compressor-az-function/providers/Microsoft.Storage/storageAccounts/mediablobazfct
   ```
3. Run scripts - no warnings! ✅

---

**Status:** Scripts updated to use Azure AD authentication
**Next step:** Grant yourself the Storage Blob Data Contributor role (one command above)
