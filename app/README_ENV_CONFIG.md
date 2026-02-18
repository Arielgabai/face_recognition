# Environment Variables Configuration

## Gunicorn / Server

| Variable | Default | Description |
|---|---|---|
| `PORT` | `10000` | HTTP listen port |
| `GUNICORN_WORKERS` | `3` | Number of Gunicorn workers |
| `GUNICORN_THREADS` | `2` | Threads per worker (I/O parallelism) |
| `GUNICORN_TIMEOUT` | `90` | Request timeout in seconds |
| `GUNICORN_LOGLEVEL` | `info` | Log level: debug, info, warning, error, critical |
| `GUNICORN_GRACEFUL_TIMEOUT` | `30` | Graceful shutdown timeout |
| `GUNICORN_KEEPALIVE` | `5` | Keep-alive seconds |
| `GUNICORN_MAX_REQUESTS` | `0` | Worker recycling (0 = disabled) |

## Matching / Concurrency

| Variable | Default | Description |
|---|---|---|
| `MATCHING_THREAD_POOL_SIZE` | `1` | Thread pool for background selfie matching |
| `SELFIE_MATCH_CAN_INDEX_MISSING_PHOTOS` | `0` | Allow selfie flow to index missing photos (0=no, 1=yes) |
| `SELFIE_MATCH_INDEX_LIMIT` | `5` | Max photos to index per event during selfie match (if enabled) |
| `SELFIE_MATCHING_DISABLED` | `0` | Completely disable selfie matching (emergency switch) |

## AWS Rekognition

| Variable | Default | Description |
|---|---|---|
| `REKOGNITION_REGION` | `eu-west-1` | AWS region for Rekognition |
| `AWS_BOTO_CONNECT_TIMEOUT` | `3` | Boto3 connection timeout (seconds) |
| `AWS_BOTO_READ_TIMEOUT` | `20` | Boto3 read timeout (seconds) |
| `AWS_BOTO_MAX_ATTEMPTS` | `3` | Boto3 retry max attempts |
| `AWS_CONCURRENT_REQUESTS` | `10` | Max concurrent Rekognition API calls |
| `AWS_REKOGNITION_FACE_THRESHOLD` | `60` | Face match similarity threshold |
| `AWS_REKOGNITION_SEARCH_MAXFACES` | `10` | Max faces returned by SearchFaces |
| `AWS_REKOGNITION_SELFIE_SEARCH_MAXFACES` | `500` | Max faces for selfie SearchFaces |
| `AWS_REKOGNITION_PURGE_AUTO` | `false` | Auto-purge stale faces from collection |

## User Lifecycle

| Variable | Default | Description |
|---|---|---|
| `PENDING_SELFIE_TTL_MINUTES` | `60` | Deactivate pending users after N minutes (admin cleanup endpoint) |

## Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./face_recognition.db` | Database connection string |
| `DB_POOL_SIZE` | `10` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | `20` | SQLAlchemy max overflow |
| `DB_POOL_RECYCLE` | `1800` | Pool recycle time (seconds) |
| `DB_POOL_TIMEOUT` | `30` | Pool connection timeout |

## Manual Testing Checklist

### Concurrent Account Creation + Selfie Upload
1. Start the application
2. Create 3 user accounts in parallel (use `register-with-event-code`)
3. Verify all 3 accounts have `selfie_status="pending"`
4. Upload selfies for all 3 users in parallel
5. Verify API responds for each (HTTP 200)
6. Poll `/api/rematch-status` until all show `selfie_status="valid"`

### PhotoFace Table Verification
1. Upload photos to an event (photographer flow)
2. Query `photo_faces` table: `SELECT * FROM photo_faces WHERE event_id = ?`
3. Verify face_ids are populated after photo indexation
4. Delete a photo and verify its `photo_faces` rows are cleaned up

### No ListFaces Calls
1. Search the final codebase: `grep -r "list_faces" app/aws_face_recognizer.py`
2. Only comments should match; no actual `self.client.list_faces(...)` calls should exist

### Pending User Cleanup
1. Create a user with `register-with-event-code` (will have `selfie_status="pending"`)
2. Wait > `PENDING_SELFIE_TTL_MINUTES` (or set it to 1 for testing)
3. Call `POST /api/admin/cleanup-pending-users`
4. Verify user is deactivated (`is_active=False`)
