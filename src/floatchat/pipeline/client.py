"""
ARGO API Client - Direct access to THREDDS OPeNDAP
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import xarray as xr
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ArgoAPIClient:
    """
    Direct API access to ARGO data via THREDDS OPeNDAP
    No file downloads required!
    """
    
    def __init__(self, base_url: str = "https://www.ncei.noaa.gov/thredds-ocean"):
        self.base_url = base_url
        self.catalog_base = f"{base_url}/catalog/argo/gadr"
        self.opendap_base = f"{base_url}/dodsC/argo/gadr"
        
        # Configure retry strategy
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
    def list_data_centers(self) -> List[str]:
        """List available ARGO data centers via API"""
        catalog_url = f"{self.catalog_base}/catalog.html"
        logger.info(f"Fetching data centers...")
        
        try:
            response = self.session.get(catalog_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            centers = []
            for img in soup.find_all('img'):
                if img.get('alt') in ['[DIR]', 'Folder']:
                    parent = img.find_parent('tr')
                    if parent:
                        link = parent.find('a')
                        if link:
                            center_name = link.text.strip().strip('/')
                            if center_name and center_name not in centers:
                                centers.append(center_name)
            
            logger.info(f"Found {len(centers)} data centers")
            return sorted(list(set(centers)))
        except Exception as e:
            logger.error(f"Error: {e}")
            # Fallback to known centers
            return ['aoml', 'atlantic', 'bodc', 'coriolis', 'csio', 'csiro', 
                    'incois', 'indian', 'jma', 'kiost', 'kma', 'kordi', 
                    'meds', 'nmdis', 'pacific']
    
    def list_floats(self, data_center: str, max_floats: Optional[int] = None) -> List[str]:
        """List available float IDs via API"""
        catalog_url = f"{self.catalog_base}/{data_center}/catalog.html"
        logger.info(f"Fetching floats from {data_center}...")
        
        try:
            response = self.session.get(catalog_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            floats = []
            for img in soup.find_all('img'):
                if img.get('alt') in ['[DIR]', 'Folder']:
                    parent = img.find_parent('tr')
                    if parent:
                        link = parent.find('a')
                        if link:
                            float_id = link.text.strip().strip('/')
                            if float_id.isdigit():
                                floats.append(float_id)
                                if max_floats and len(floats) >= max_floats:
                                    break
            
            logger.info(f"Found {len(floats)} floats")
            return sorted(floats)
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
    
    def get_opendap_url(self, data_center: str, float_id: str) -> Optional[str]:
        """
        Resolve the correct OPeNDAP URL by scraping the float's catalog page.
        This handles variable filenames (e.g., 'nodc_' prefix).
        """
        catalog_url = f"{self.catalog_base}/{data_center}/{float_id}/catalog.html"
        try:
            response = self.session.get(catalog_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the profile file link (ends with 'prof.nc')
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'prof.nc' in href and 'catalog.html' in href:
                    # Extract dataset path from query param if present, or parse href
                    # Standard THREDDS catalog link: catalog.html?dataset=...
                    if 'dataset=' in href:
                        dataset_path = href.split('dataset=')[1]
                        return f"{self.base_url}/dodsC/{dataset_path}"
                    
            # Fallback for simple links
            for link in soup.find_all('a'):
                text = link.text.strip()
                if text.endswith('prof.nc'):
                    # Construct default path
                    return f"{self.opendap_base}/{data_center}/{float_id}/{text}"
                    
        except Exception as e:
            logger.warning(f"Could not resolve URL for {float_id}: {e}")
            
        # Fallback to standard naming
        return f"{self.opendap_base}/{data_center}/{float_id}/{float_id}_prof.nc"
    
    def download_file(self, url: str, float_id: str) -> Optional[str]:
        """Download file and return path"""
        try:
            # Convert OPeNDAP URL to HTTPS file server URL
            # OPeNDAP: .../dodsC/...
            # HTTPS:   .../fileServer/...
            file_url = url.replace('/dodsC/', '/fileServer/')
            
            local_filename = f"temp_{float_id}.nc"
            logger.info(f"Downloading {file_url} to {local_filename}...")
            
            with self.session.get(file_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return local_filename
        except Exception as e:
            logger.error(f"Download failed for {float_id}: {e}")
            return None

    def fetch_float_data(self, data_center: str, float_id: str) -> tuple[Optional[xr.Dataset], Optional[str]]:
        """
        Fetch float data via OPeNDAP or fallback to download.
        Returns (dataset, local_filepath)
        """
        url = self.get_opendap_url(data_center, float_id)
        if not url:
            return None, None
            
        logger.info(f"Fetching {float_id}...")
        
        # Method 1: Try OPeNDAP Streaming first
        try:
            ds = xr.open_dataset(url, decode_times=False)
            # Test access to ensure it's working
            _ = ds.sizes
            logger.info(f"✓ Accessed via OPeNDAP: {float_id}")
            return ds, None
        except Exception as e:
            logger.warning(f"OPeNDAP failed for {float_id}, falling back to download. Error: {e}")
            
        # Method 2: Fallback to download
        local_file = self.download_file(url, float_id)
        if local_file:
            try:
                ds = xr.open_dataset(local_file, decode_times=False)
                ds.load() # Load into memory so we can close/delete file
                ds.close() # Close file handle
                logger.info(f"✓ Downloaded and loaded: {float_id}")
                return ds, local_file
            except Exception as e:
                logger.error(f"Failed to open downloaded file {float_id}: {e}")
                # Clean up if open failed
                try:
                    import os
                    os.remove(local_file)
                except:
                    pass
                    
        return None, None
