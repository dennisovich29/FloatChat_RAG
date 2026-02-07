"""
ARGO Pipeline Runner - Orchestrates data fetching and processing
"""

import logging
import queue
import threading
import xarray as xr
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from .client import ArgoAPIClient
from .processor import ArgoStreamProcessor

logger = logging.getLogger(__name__)


def stream_multiple_floats(data_center: str, num_floats: int = 10, 
                          db_url: str = "sqlite:///data/databases/argo_data.db",
                          save_parquet: bool = True):
    """
    Stream multiple floats directly from API to SQL/Parquet
    NO DOWNLOADS REQUIRED!
    """
    
    # Initialize
    api = ArgoAPIClient()
    processor = ArgoStreamProcessor()
    
    # Get float list
    logger.info(f"Fetching float list from {data_center}...")
    floats = api.list_floats(data_center, max_floats=num_floats)
    
    if not floats:
        logger.error("No floats found!")
        return
    
    # Queue for DB writes
    write_queue = queue.Queue()
    
    # Thread-safe counter
    success_count = [0]
    
    def db_writer():
        """Consumer thread to write data to SQL/Parquet sequentially"""
        logger.info("DB Writer started")
        active = True
        while active or not write_queue.empty():
            try:
                # Get item with timeout to allow checking 'active' flag
                item = write_queue.get(timeout=1)
                
                type_ = item.get('type')
                
                if type_ == 'DONE':
                    active = False
                    write_queue.task_done()
                    continue
                
                if type_ == 'DATA':
                    float_id = item['float_id']
                    ds = item['dataset']
                    
                    try:
                        # Stream to SQL
                        processor.stream_to_sql(ds, float_id, data_center, db_url)
                        
                        # Stream to Parquet (optional)
                        if save_parquet:
                            processor.stream_to_parquet(ds, float_id, data_center)
                            
                        success_count[0] += 1
                        ds.close() # Close dataset after writing
                    except Exception as e:
                        logger.error(f"Error writing {float_id}: {e}")
                    finally:
                        write_queue.task_done()
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"DB Writer error: {e}")
                
        logger.info("DB Writer finished")

    def fetch_worker(float_id):
        """Producer function to fetch data"""
        import os
        try:
            ds, local_file = api.fetch_float_data(data_center, float_id)
            if ds:
                # Force load data into memory if not already done (for OPeNDAP case)
                if not local_file:
                    try:
                        logger.info(f"Loading data for {float_id} into memory...")
                        ds.load()
                        logger.info(f"✓ Data loaded for {float_id}")
                    except Exception as load_error:
                        # If load fails, close dataset and try download fallback
                        logger.warning(f"OPeNDAP load failed for {float_id}: {load_error}")
                        try:
                            ds.close()
                        except:
                            pass
                        
                        # Try download fallback
                        logger.info(f"Attempting download fallback for {float_id}...")
                        url = api.get_opendap_url(data_center, float_id)
                        if url:
                            local_file = api.download_file(url, float_id)
                            if local_file:
                                try:
                                    ds = xr.open_dataset(local_file, decode_times=False)
                                    ds.load()
                                    ds.close()
                                    logger.info(f"✓ Downloaded and loaded: {float_id}")
                                except Exception as e:
                                    logger.error(f"Download fallback also failed for {float_id}: {e}")
                                    if local_file and os.path.exists(local_file):
                                        os.remove(local_file)
                                    return False
                            else:
                                return False
                        else:
                            return False

                # Put dataset in queue for writing
                write_queue.put({'type': 'DATA', 'float_id': float_id, 'dataset': ds})
                
                # Cleanup local file if it exists
                if local_file and os.path.exists(local_file):
                    os.remove(local_file)
                    logger.info(f"Cleaned up temp file for {float_id}")
                    
                return True
        except Exception as e:
            logger.error(f"Error fetching {float_id}: {e}")
        return False

    # Start DB writer thread
    writer_thread = threading.Thread(target=db_writer)
    writer_thread.start()

    # Use ThreadPoolExecutor for parallel fetching
    logger.info(f"Starting parallel processing for {len(floats)} floats...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_worker, fid): fid for fid in floats}
        
        for future in as_completed(futures):
            # We just wait for them to finish pushing to queue
            pass
            
    # Signal writer to stop
    write_queue.put({'type': 'DONE'})
    writer_thread.join()

    # Create indexes
    if success_count[0] > 0:
        processor.create_indexes(db_url)
    
    logger.info(f"\n✓ Complete! Successfully processed {success_count[0]}/{len(floats)} floats")
    logger.info(f"  Database: {db_url}")
    if save_parquet:
        logger.info(f"  Parquet files: {processor.output_dir}/")
