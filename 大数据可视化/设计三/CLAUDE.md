# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains the source code for NutriAI, an AI-assisted diet management application.
The project is currently divided into:
- `frontend`: An Android native application built with Kotlin, Jetpack Compose, and Material 3.
- `backend`: An empty directory that is slated to contain a Python/FastAPI backend using PostgreSQL (per the docs).
- `docs`: Extensive product requirement documents (PRD) and backend design/implementation phase plans.
- `examples`: UI mockups and design assets.

## Architecture

### Frontend
- **Tech Stack:** Kotlin, Android SDK, Jetpack Compose, Material 3, Room Database, Retrofit.
- **Structure:** Located in `frontend/app/src/main/java/com/example/`.
- **Database:** Local Room database for diet records.
- **AI Integration:** Uses Gemini for text/food recognition to estimate nutritional info.

### Backend (Planned)
- **Tech Stack:** Python, FastAPI, Uvicorn, Pydantic, PostgreSQL.
- **Structure (Planned):**
  ```
  backend/
    app/
      main.py
      api/v1/
      core/
      models/
      schemas/
      crud/
      db/
  ```
- **Note:** The backend directory is currently empty. Future tasks involve following the `docs/后端开发阶段*.md` files to build out the API.

## Common Commands

### Frontend (Android)
Since `gradlew` wrapper isn't checked into the frontend directory, you will likely need to rely on Android Studio to build, or run Gradle if installed system-wide:

- **Build APK:**
  ```bash
  cd frontend
  gradle build
  ```
- **Run Tests:**
  ```bash
  cd frontend
  gradle test
  ```
- **Run Android Linter:**
  ```bash
  cd frontend
  gradle lint
  ```

### Backend (Future Python/FastAPI)
Once the backend is initialized based on the phase 01 document:
- **Install dependencies:** `pip install -r requirements.txt` (or via pipenv/poetry when chosen)
- **Run Dev Server:** `cd backend && uvicorn app.main:app --reload`
- **Run Tests:** `cd backend && pytest`

## Development Notes

- **Frontend Environment Variables:** A `.env` file is required in the `frontend` directory. Copy `.env.example` to `.env` and configure `GEMINI_API_KEY`.
- **Backend Documentation:** The `docs` folder contains step-by-step implementation plans for the backend (`后端开发阶段01` through `09`). Follow these documents closely when working on backend tasks.
- **Current MVP Status:** The Android frontend currently uses mock data/camera or a local Room database as fallbacks if the Gemini API isn't fully connected. Full user authentication is out of scope for the MVP phase.
