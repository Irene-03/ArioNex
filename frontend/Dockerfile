# ================================================================
#   داکرفایل دو مرحله‌ای کلاینت ری‌اکت آریونکس (ArioNex Frontend Dockerfile)
#   رویکرد بیلد بهینه و توزیع تحت وب‌سرور قدرتمند و فوق‌سبک Nginx
# ================================================================

# --- مرحله ۱: بیلد و کمپایل فایل‌های جاوااسکریپت و استایل‌ها ---
FROM node:20-slim AS builder

WORKDIR /app

# کپی فیزیکی پیکربندی پکیج‌ها و نصب ملزومات
# (lockfile همراه package.json کپی می‌شود تا از کش بیلد بهره ببریم)
COPY package.json package-lock.json /app/

# استفاده از mirror برای نصب سریع‌تر پکیج‌ها
RUN npm config set registry https://registry.npmmirror.com \
    && npm install --no-audit --no-fund \
    && npm config delete registry

# کپی سورس‌های فرانت‌اند و کامپایل نهایی با Vite
COPY . /app/
RUN npm run build

# --- مرحله ۲: خدمت‌رسانی و توزیع فایل‌های ایستای کامپایل شده ---
FROM nginx:alpine

# کپی خروجی بیلد مرحله اول به پوشه وب‌سرور Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# کپی پیکربندی Nginx جهت پشتیبانی از آدرس‌های SPA ری‌اکت
COPY nginx.conf /etc/nginx/conf.d/default.conf

# پورت پیش‌فرض وب‌سرور
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
