# Repository Rename Instructions

Follow these steps to rename the repository from `DarkHorses-Backend` to `DarkHorses-Backend-Workers`.

## Step 1: Rename on GitHub

1. Go to: https://github.com/mattbarb/DarkHorses-Backend
2. Click **Settings** (top right)
3. In the **General** section, find **Repository name**
4. Change to: `DarkHorses-Backend-Workers`
5. Click **Rename**

GitHub will automatically redirect the old URL to the new one, but it's best to update the remote.

## Step 2: Update Git Remote (From Current Directory)

```bash
# Update the remote URL to point to new repo name
git remote set-url origin https://github.com/mattbarb/DarkHorses-Backend-Workers.git

# Verify the change
git remote -v
```

Should now show:
```
origin  https://github.com/mattbarb/DarkHorses-Backend-Workers.git (fetch)
origin  https://github.com/mattbarb/DarkHorses-Backend-Workers.git (push)
```

## Step 3: Rename Local Directory

**Important**: You must be OUTSIDE the directory to rename it.

```bash
# Navigate to parent directory
cd /Users/matthewbarber/Documents/GitHub/

# Rename the directory
mv DarkHorses-Backend DarkHorses-Backend-Workers

# Navigate into the renamed directory
cd DarkHorses-Backend-Workers
```

## Step 4: Verify Everything Works

```bash
# Check git status
git status

# Check remote
git remote -v

# Make a test commit (optional)
git add .
git commit -m "Rename repository to DarkHorses-Backend-Workers"
git push
```

## Complete! ✅

Your repository is now:
- **GitHub**: `https://github.com/mattbarb/DarkHorses-Backend-Workers`
- **Local**: `/Users/matthewbarber/Documents/GitHub/DarkHorses-Backend-Workers`

## Notes

- All documentation has already been updated to reference the new name
- The old GitHub URL will redirect automatically (GitHub feature)
- Local clones by others will continue to work with old URL (redirect)
- Update any bookmarks or links to use the new URL
