# Deploying Sales Forecasting App to Azure App Service (Portal UI)

This guide walks through deploying the Flask application to **Azure App Service** using the Azure Portal — no CLI required.

---

## Prerequisites

- An active [Azure account](https://portal.azure.com)
- The project code pushed to a **GitHub** repository (or a local ZIP ready to upload)
- `requirements.txt` and `startup.txt` already present in the project root

---

## Step 1: Create a Resource Group

1. Sign in to the [Azure Portal](https://portal.azure.com).
2. Search for **Resource groups** in the top search bar and select it.
3. Click **+ Create**.
4. Choose your **Subscription**.
5. Enter a **Resource group name** (e.g. `sales-forecasting-rg`).
6. Select a **Region** close to your users (e.g. `West Europe`).
7. Click **Review + create** → **Create**.

---

## Step 2: Create an App Service Plan

1. Search for **App Service plans** in the top search bar.
2. Click **+ Create**.
3. Select the **Resource group** you just created.
4. Enter a **Name** (e.g. `sales-forecasting-plan`).
5. Set **Operating System** to **Linux**.
6. Select your **Region** (same as the resource group).
7. Under **Pricing plan**, choose a tier:
   - **Free (F1)** — for testing (limited resources, may be slow for ML workloads).
   - **Basic (B1)** or higher — recommended for production use with scikit-learn/statsmodels.
8. Click **Review + create** → **Create**.

---

## Step 3: Create the Web App

1. Search for **App Services** in the top search bar.
2. Click **+ Create** → **Web App**.
3. Fill in the **Basics** tab:
   - **Subscription**: your subscription.
   - **Resource Group**: `sales-forecasting-rg`.
   - **Name**: a globally unique name (e.g. `sales-forecasting-app`). This becomes your URL: `https://sales-forecasting-app.azurewebsites.net`.
   - **Publish**: **Code**.
   - **Runtime stack**: **Python 3.12** (or latest available).
   - **Operating System**: **Linux**.
   - **Region**: same as before.
   - **App Service Plan**: select `sales-forecasting-plan`.
4. Click **Review + create** → **Create**.
5. Wait for the deployment to complete, then click **Go to resource**.

---

## Step 4: Configure Application Settings

1. In your Web App resource, go to **Settings** → **Environment variables**.
2. Under **App settings**, click **+ Add** and create the following:
   | Name | Value |
   |------|-------|
   | `SECRET_KEY` | A strong random string (e.g. generate one at https://randomkeygen.com) |
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |
3. Click **Apply** and confirm.

---

## Step 5: Configure the Startup Command

1. In your Web App resource, go to **Settings** → **Configuration** → **General settings**.
2. In the **Startup Command** field, enter:
   ```
   gunicorn --bind=0.0.0.0 --timeout 600 run:app
   ```
3. Click **Save**.

> This matches the `startup.txt` in your project. The extended timeout (600s) accommodates the ML library preloading on first request.

---

## Step 6: Deploy Your Code

You have two options: **GitHub deployment** (recommended) or **ZIP deploy**.

### Option A: Deploy from GitHub (Recommended)

1. In your Web App resource, go to **Deployment** → **Deployment Center**.
2. Under **Source**, select **GitHub**.
3. Click **Authorize** and sign into your GitHub account.
4. Select your **Organization**, **Repository**, and **Branch** (e.g. `main`).
5. Under **Build provider**, choose **App Service Build Service (Oryx)**.
6. Click **Save**.
7. Azure will automatically pull, build, and deploy your app. You can monitor progress under **Deployment Center** → **Logs**.

> Every push to the selected branch will trigger an automatic redeployment.

### Option B: Deploy via ZIP Upload

1. Create a ZIP file of your entire project folder (include `run.py`, `requirements.txt`, `startup.txt`, `app/`, and `data/` at the root of the ZIP).
2. In the Azure Portal, navigate to your Web App.
3. Go to **Deployment** → **Deployment Center**.
4. Under **Source**, select **Local Git** or use the **Advanced Tools (Kudu)** method:
   - Go to **Development Tools** → **Advanced Tools** → **Go →**.
   - In the Kudu portal, click **Tools** → **Zip Push Deploy**.
   - Drag and drop your ZIP file into the page.
5. Wait for the deployment to finish.

---

## Step 7: Verify the Deployment

1. Go back to your Web App **Overview** page.
2. Click the **Default domain** link (e.g. `https://sales-forecasting-app.azurewebsites.net`).
3. The app should load. The first request may take 30–60 seconds as the ML libraries initialize.

---

## Step 8: Monitor & Troubleshoot

### View Logs
1. Go to **Monitoring** → **Log stream** in your Web App to see real-time stdout/stderr output.
2. For historical logs, go to **Monitoring** → **App Service logs**:
   - Set **Application Logging** to **File System**.
   - Set **Level** to **Information** or **Verbose**.
   - Click **Save**.
   - View logs under **Monitoring** → **Log stream** or download from **Advanced Tools (Kudu)**.

### Common Issues

| Issue | Solution |
|-------|----------|
| App shows "Application Error" | Check **Log stream** for Python errors. Ensure `requirements.txt` is correct. |
| Deployment fails at `pip install` | Ensure `SCM_DO_BUILD_DURING_DEPLOYMENT` is set to `true`. |
| App is very slow or times out | Upgrade to at least **B1** plan. ML libraries need more memory than Free tier provides. |
| `ModuleNotFoundError` | Verify all dependencies are listed in `requirements.txt`. Add any missing ones (e.g. `python-dotenv`). |
| 502 Bad Gateway | Check if `gunicorn` is in `requirements.txt` and the startup command is correct. |

---

## Step 9: Set Up Custom Domain (Optional)

1. Go to **Settings** → **Custom domains**.
2. Click **+ Add custom domain**.
3. Enter your domain name and follow the DNS verification steps (add CNAME/TXT records at your domain registrar).
4. After verification, click **Add**.
5. To enable HTTPS, go to **TLS/SSL settings** → **Bindings** and create a free App Service Managed Certificate.

---

## Estimated Costs

| Tier | Price (approx.) | Notes |
|------|-----------------|-------|
| Free (F1) | $0/month | 60 min CPU/day, 1 GB RAM — not suitable for ML workloads |
| Basic (B1) | ~$13/month | 1 core, 1.75 GB RAM — minimum recommended |
| Standard (S1) | ~$69/month | Auto-scale, staging slots, backups |

---

## Project File Reference

| File | Purpose |
|------|---------|
| `run.py` | App entry point — creates and runs the Flask app |
| `requirements.txt` | Python dependencies installed during deployment |
| `startup.txt` | Startup command reference (`gunicorn --bind=0.0.0.0 --timeout 600 run:app`) |
| `app/` | Application package (routes, templates, forecast engine) |
| `data/` | CSV datasets and currency metadata |
