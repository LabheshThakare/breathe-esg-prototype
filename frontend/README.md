# Frontend

Simple React dashboard for analyst review.

## Run Locally

Start the Django backend first:

```bash
cd ../backend
python3 manage.py runserver
```

Then start the frontend:

```bash
cd ../frontend
npm install
npm run dev
```

The app reads from:

```text
http://127.0.0.1:8000/api
```

Override with:

```bash
VITE_API_BASE_URL=https://your-backend.example.com/api npm run dev
```

