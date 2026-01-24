# "Build Windows exe" not showing in GitHub Actions?

The workflow only appears if the file is **on GitHub** and on the branch you’re viewing.

## 1. Commit and push the workflow

In your project folder:

```bash
git add .github/
git status   # you should see .github/workflows/build-windows.yml
git commit -m "Add Build Windows exe workflow"
git push origin main
```

Use `master` or `develop` if that’s your default branch.

## 2. Check the file is on GitHub

Open (replace `YOUR_USER`, `YOUR_REPO`, and `main` if you use another branch):

**https://github.com/YOUR_USER/YOUR_REPO/blob/main/.github/workflows/build-windows.yml**

- **You see the YAML** → file is pushed; the workflow should show in Actions.
- **404** → file isn’t on that branch; run step 1 and push to that branch.

## 3. Where to find it in the Actions tab

1. Repo on GitHub → **Actions**.
2. In the **left sidebar**, under **“All workflows”**, click **“Build Windows exe”**.
3. **“Run workflow”** (top right) → **“Run workflow”**.
4. When the run is green ✓ → open it → **Artifacts** → download **AttendanceTracker-Windows**.

If **“Build Windows exe”** is still not in the left sidebar, the workflow file isn’t on the branch you’re viewing. Push `.github/` to that branch.
