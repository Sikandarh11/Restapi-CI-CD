# Restapi-CI-CD

A Flask-based REST API that demonstrates a simple **CI/CD pipeline** approach using **GitHub Actions** and deployment to **Azure Web Apps**.  
The API includes:
- **Auth** (register/login) using **MongoDB** + **JWT**
- **Posts CRUD** backed by **MongoDB**
- **Thumbnail upload** to **Firebase Storage**
- Containerization via **Docker**
- Example GitHub Actions workflows for **Azure deploy** (code deploy + container deploy)

---

## Tech Stack

- **Backend**: Python, Flask
- **Database**: MongoDB (via `pymongo` / `Flask-PyMongo`)
- **Auth**: bcrypt password hashing + JWT access/refresh tokens
- **File Storage**: Firebase Admin SDK + Firebase Storage bucket
- **Deployment**: Azure Web App (GitHub Actions)
- **Container**: Docker

Key dependencies (from `requirements.txt`):
- Flask, Flask-RESTful, Flask-PyMongo
- pymongo
- PyJWT
- bcrypt, cryptography
- firebase-admin
- gunicorn (production server option)

---

## Repository Structure (high-level)

```text
.
├─ app.py                         # Flask entrypoint (registers blueprints)
├─ extensions.py                  # Flask app + Mongo client/db initialization
├─ requirements.txt               # Python dependencies
├─ Dockerfile                     # Container build instructions
├─ blueprints/
│  ├─ auth.py                     # /register, /login, token_required, refresh
│  ├─ post.py                     # /posts CRUD + comments + reactions + firebase uploads
│  └─ init.py                     # (blueprints package init file)
└─ .github/workflows/
   ├─ azure-webapp-cicd.yml        # Simple build+deploy pipeline (webapps-deploy v2)
   ├─ main_restapicicd.yml         # Build artifact + deploy to Azure (OIDC login)
   └─ main_restapiflaskwebapp.yml  # Build/push Docker image + deploy container to Azure
```

---

## How the App Works

### Flask App Entrypoint (`app.py`)
- Imports the shared Flask app instance from `extensions.py`
- Registers two blueprints:
  - `auth_bp` (authentication)
  - `posts_bp` (posts endpoints)
- Exposes a simple home route `/` rendering `templates/index.html` (if present)
- Runs on `0.0.0.0:80`

---

## API Endpoints

> Note: Most endpoints in this project read data from `request.form` and files from `request.files`, so **`multipart/form-data`** is commonly used instead of JSON.

### Authentication (`blueprints/auth.py`)

#### `POST /register`
Registers a new user.

**Form fields**
- `username`
- `password`

**Responses**
- `200`: SignUp successfully
- `404`: Missing data
- `500`: Signup error

Example (curl):
```bash
curl -X POST http://localhost:80/register \
  -F "username=testuser" \
  -F "password=pass123"
```

#### `POST /login`
Logs a user in and returns JWT tokens.

**Form fields**
- `username`
- `password`

**Response (200)**
- `Access Token`
- `Refresh Token`

Example (curl):
```bash
curl -X POST http://localhost:80/login \
  -F "username=testuser" \
  -F "password=pass123"
```

#### Auth Header
Protected routes use:
- Header: `x-access-token: <JWT_ACCESS_TOKEN>`

---

### Posts (`blueprints/post.py`)

All posts routes are protected with `@token_required`.

#### `GET /posts/<id>`
Fetch a post by Mongo ObjectId.

Example:
```bash
curl -X GET "http://localhost:80/posts/<POST_OBJECT_ID>" \
  -H "x-access-token: <ACCESS_TOKEN>"
```

#### `POST /posts`
Create a post and upload a thumbnail to Firebase Storage.

**Form fields**
- `title` (required)
- `text` (required)
- `tags` (required)
- File: `thumbnail` (required)

Example:
```bash
curl -X POST http://localhost:80/posts \
  -H "x-access-token: <ACCESS_TOKEN>" \
  -F "title=My Post" \
  -F "text=Hello world" \
  -F "tags=flask" \
  -F "thumbnail=@./thumb.png"
```

#### `PUT /posts/<post_id>`
Update post fields and optionally upload a new thumbnail.

**Form fields (optional)**
- `title`
- `text`
- `tags`
- `comments`
- File: `thumbnail`

#### `DELETE /posts/<post_id>`
Delete a post (only if you are the author).

#### Comments
- `POST /posts/comments/<post_id>` with form field `comments`
- `DELETE /posts/comments/<post_id>` with form field `comments`
- `PUT /posts/comments/<post_id>` with form fields `pre_comment`, `new_comment`

#### Reactions
- `PUT /posts/reactions/<post_id>` with form field `action` = `like` or `dislike`

---

## Configuration

### MongoDB
MongoDB is initialized in `extensions.py` via a MongoDB connection string and database name.

**Important**
- The repo currently contains a hard-coded MongoDB URI in `extensions.py`. For a real project, this should be moved to environment variables.

A recommended pattern:
- `MONGO_URI` environment variable
- Load with `os.environ.get("MONGO_URI")`

The `Dockerfile` already includes an example `ENV MONGO_URI=...`, but the Python code must read it for it to take effect.

---

### JWT Secret Key
The JWT secret key is set in `extensions.py`:

- `app.config['SECRET_KEY'] = 'your_secret_key'`

For production:
- store it in an environment variable (e.g., `SECRET_KEY`)
- rotate it if exposed

---

### Firebase Storage
Posts blueprint initializes Firebase using a service account JSON file and a bucket name.

Requirements:
- A Firebase service account JSON key file (currently referenced in code)
- Correct bucket name configured inside `firebase_admin.initialize_app(...)`

---

## Running Locally (without Docker)

### 1) Create a virtual environment
```bash
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Run the app
```bash
python app.py
```

App runs at:
- `http://localhost/` (port 80)

If port 80 requires admin privileges on your OS, you can change the port in `app.py` to something like `5000`:
```python
app.run(host='0.0.0.0', port=5000)
```

---

## Running with Docker

### Build image
```bash
docker build -t restapi-ci-cd .
```

### Run container
```bash
docker run --rm -p 8080:80 restapi-ci-cd
```

Now the app should be accessible at:
- `http://localhost:8080`

> Note: You must also ensure MongoDB connectivity and Firebase credentials are configured properly for the container runtime.

---

## CI/CD with GitHub Actions (Azure)

This repository contains multiple workflows under `.github/workflows/`:

### 1) `azure-webapp-cicd.yml`
A simple pipeline:
- checkout
- setup python 3.9
- install requirements
- deploy via `azure/webapps-deploy@v2`

Uses secrets:
- `AZURE_WEBAPP_NAME`
- `AZURE_PUBLISH_PROFILE`

### 2) `main_restapicicd.yml`
A more structured pipeline:
- build job creates `release.zip` artifact
- deploy job downloads artifact
- logs in to Azure using `azure/login@v2` (OIDC)
- deploys with `azure/webapps-deploy@v3`

Uses secrets (example names in workflow):
- `AZUREAPPSERVICE_CLIENTID_...`
- `AZUREAPPSERVICE_TENANTID_...`
- `AZUREAPPSERVICE_SUBSCRIPTIONID_...`

### 3) `main_restapiflaskwebapp.yml`
Container-based pipeline:
- build and push Docker image to Azure Container Registry
- deploy image to Azure Web App using publish profile

Uses secrets:
- `AzureAppService_ContainerUsername_...`
- `AzureAppService_ContainerPassword_...`
- `AzureAppService_PublishProfile_...`

---

## Security Notes / Recommendations

If you intend to use this as a real deployment template, strongly consider:
- Remove any committed credentials/service account JSON from git history
- Move Mongo URI + SECRET_KEY + Firebase config to environment variables or GitHub Secrets
- Use JSON request bodies (`request.get_json()`) for REST endpoints instead of only `request.form`
- Add input validation + rate limiting for auth endpoints
- Add automated tests and run them in CI (right now the workflows have placeholder “Tests passed!” steps)

---

## Troubleshooting

### MongoDB connection errors
- Verify your MongoDB Atlas IP whitelist includes your machine/runner/container
- Confirm the database name exists and user has permissions
- Ensure the connection string is valid

### Firebase errors
- Ensure the service account JSON file exists at the path referenced in code
- Verify the bucket name matches your Firebase Storage bucket
- Verify permissions for the service account

### 403 "Token is missing!"
- Add `x-access-token` header with your access token from `/login`

---

## License

No license file is currently included. If you want, add an open-source license (MIT/Apache-2.0/etc.) to clarify usage.

---

## Author

Maintained by `Sikandarh11`.
