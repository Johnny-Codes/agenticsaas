# Tasks

This folder contains the celery tasks. **When creating or changing existing tasks, you must restart the celery container so celery can register the tasks. I learned this the hard way.**

## Creating tasks

- Add file to imports in `celery_app.py`
- Must restart celery container when changes have been made
- The initial call can by sync and the helper functions can be async