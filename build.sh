#!/usr/bin/env bash
# Render "Build Command" olarak kullanın: ./build.sh
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# django-tenants: public şema + tüm tenant şemaları için migration.
# Normal "migrate" TENANT_APPS'i public şemaya uygulamaz; migrate_schemas şart.
python manage.py migrate_schemas --shared
python manage.py migrate_schemas
