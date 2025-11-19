"""
Cloud Storage Manager
=====================
Handles photo uploads to cloud storage (Cloudinary) or local filesystem.

Environment Variables:
- USE_LOCAL_STORAGE: true/false (default: true for development)
- CLOUDINARY_CLOUD_NAME: Your Cloudinary cloud name
- CLOUDINARY_API_KEY: Your Cloudinary API key
- CLOUDINARY_API_SECRET: Your Cloudinary API secret
- CLOUDINARY_FOLDER: Folder name in Cloudinary (default: resellgenie)
"""

import os
from typing import Optional, List, Tuple
from pathlib import Path
import uuid


class CloudStorageManager:
    """Manages photo storage - either local or cloud"""

    def __init__(self):
        self.use_local = os.getenv('USE_LOCAL_STORAGE', 'true').lower() == 'true'

        if not self.use_local:
            # Initialize Cloudinary
            try:
                import cloudinary
                import cloudinary.uploader

                cloudinary.config(
                    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                    api_key=os.getenv('CLOUDINARY_API_KEY'),
                    api_secret=os.getenv('CLOUDINARY_API_SECRET')
                )

                self.cloudinary = cloudinary
                self.cloudinary_folder = os.getenv('CLOUDINARY_FOLDER', 'resellgenie')
                print("✅ Cloudinary configured for photo storage")
            except ImportError:
                print("⚠️  Cloudinary not installed - falling back to local storage")
                self.use_local = True
            except Exception as e:
                print(f"⚠️  Cloudinary configuration error: {e}")
                self.use_local = True

        if self.use_local:
            print("📁 Using local storage for photos")
            # Ensure local directories exist
            self.upload_dir = Path('data/uploads')
            self.draft_dir = Path('data/draft_photos')
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            self.draft_dir.mkdir(parents=True, exist_ok=True)

    def upload_photo(
        self,
        file_path: str,
        folder: str = 'uploads',
        public_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Upload a photo to storage.

        Args:
            file_path: Path to the photo file
            folder: Folder/category ('uploads' or 'drafts')
            public_id: Optional custom ID for the file

        Returns:
            (success: bool, url_or_path: str)
        """
        if self.use_local:
            return self._upload_local(file_path, folder, public_id)
        else:
            return self._upload_cloudinary(file_path, folder, public_id)

    def _upload_local(
        self,
        file_path: str,
        folder: str,
        public_id: Optional[str]
    ) -> Tuple[bool, str]:
        """Upload to local filesystem"""
        try:
            source = Path(file_path)

            if not source.exists():
                return False, f"File not found: {file_path}"

            # Determine destination
            if folder == 'drafts':
                dest_dir = self.draft_dir
            else:
                dest_dir = self.upload_dir

            # Generate filename
            if public_id:
                filename = f"{public_id}{source.suffix}"
            else:
                filename = f"{uuid.uuid4()}{source.suffix}"

            dest_path = dest_dir / filename

            # Copy file (or move if it's already in temp)
            import shutil
            shutil.copy2(source, dest_path)

            # Return relative path for database storage
            relative_path = str(dest_path.relative_to(Path.cwd()))
            return True, relative_path

        except Exception as e:
            return False, f"Local upload error: {str(e)}"

    def _upload_cloudinary(
        self,
        file_path: str,
        folder: str,
        public_id: Optional[str]
    ) -> Tuple[bool, str]:
        """Upload to Cloudinary"""
        try:
            # Construct folder path
            cloudinary_folder = f"{self.cloudinary_folder}/{folder}"

            # Upload options
            options = {
                'folder': cloudinary_folder,
                'resource_type': 'image'
            }

            if public_id:
                options['public_id'] = public_id

            # Upload to Cloudinary
            result = self.cloudinary.uploader.upload(file_path, **options)

            # Return secure URL
            return True, result['secure_url']

        except Exception as e:
            return False, f"Cloudinary upload error: {str(e)}"

    def delete_photo(self, url_or_path: str) -> bool:
        """
        Delete a photo from storage.

        Args:
            url_or_path: Either Cloudinary URL or local file path

        Returns:
            success: bool
        """
        if self.use_local:
            return self._delete_local(url_or_path)
        else:
            return self._delete_cloudinary(url_or_path)

    def _delete_local(self, file_path: str) -> bool:
        """Delete from local filesystem"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Local delete error: {e}")
            return False

    def _delete_cloudinary(self, url: str) -> bool:
        """Delete from Cloudinary"""
        try:
            # Extract public_id from URL
            # URL format: https://res.cloudinary.com/{cloud_name}/image/upload/{folder}/{public_id}.{ext}
            parts = url.split('/')
            if 'upload' in parts:
                upload_idx = parts.index('upload')
                public_id_with_ext = '/'.join(parts[upload_idx + 1:])
                public_id = public_id_with_ext.rsplit('.', 1)[0]

                # Delete from Cloudinary
                self.cloudinary.uploader.destroy(public_id)
                return True
        except Exception as e:
            print(f"Cloudinary delete error: {e}")
            return False

    def get_url(self, url_or_path: str) -> str:
        """
        Get publicly accessible URL for a photo.

        For local storage, returns the path (to be served by Flask).
        For Cloudinary, returns the secure URL as-is.

        Args:
            url_or_path: Either Cloudinary URL or local file path

        Returns:
            URL or path to access the photo
        """
        if self.use_local:
            # For local storage, return web-accessible path
            path = Path(url_or_path)
            return f"/{url_or_path}"
        else:
            # For Cloudinary, URL is already accessible
            return url_or_path


# Global instance
_storage = None

def get_storage() -> CloudStorageManager:
    """Get the global storage manager instance"""
    global _storage
    if _storage is None:
        _storage = CloudStorageManager()
    return _storage
