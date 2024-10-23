# build_files.sh
pip3 install -r requirements.txt
python3 manage.py collectstatic
mkdir -p staticfiles_build/media

# Check if the media directory exists and copy its contents if it does
if [ -d "media" ]; then
  cp -r media/* staticfiles_build/media/
fi