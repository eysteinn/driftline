"""
NOAA GFS wind data collector
Based on the script provided in the issue comments
"""
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple, Optional
import requests
from app.collectors.base import BaseCollector
from app.config import config

logger = logging.getLogger(__name__)

TRY_CYCLES_NEWEST_FIRST = ["18", "12", "06", "00"]


class NOAAWindCollector(BaseCollector):
    """Collector for NOAA GFS wind data"""
    
    def __init__(self, db_service, storage_service):
        super().__init__(db_service, storage_service)
        self.data_type = "wind"
        self.source = "noaa_atmos"
        self.base_url = config.NOAA_GFS_BASE_URL
        self.temp_dir = Path("/tmp/gfs_wind_data")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    

    def get_filename(self, datatype: str, yyyymmdd: str, cycle: str, fhr: int) -> str:
        return f"{datatype}.t{cycle}z.pgrb2.0p25.f{fhr:03d}.wind10m.grib2"
    

    def get_urls(self, datatype: str, yyyymmdd: str, cycle: str, fhr: int) -> Tuple[str, str]:
        """Generate GFS GRIB and index URLs"""
        key = f"{datatype}.{yyyymmdd}/{cycle}/atmos/{datatype}.t{cycle}z.pgrb2.0p25.f{fhr:03d}"
        grib_url = f"{self.base_url}/{key}"
        idx_url = f"{grib_url}.idx"
        return grib_url, idx_url
    
    def http_exists(self, url: str, timeout: int = 20) -> bool:
        """Check if a URL exists"""
        try:
            r = requests.head(url, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return True
            # some environments block HEAD; fallback to GET
            if r.status_code in (403, 405):
                r2 = requests.get(url, timeout=timeout, stream=True)
                return r2.status_code == 200
            return False
        except requests.RequestException:
            return False
    
    def fetch_text(self, url: str, timeout: int = 60) -> str:
        """Fetch text content from URL"""
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text
    
    def get_content_length(self, url: str, timeout: int = 30) -> int:
        """Get content length from URL"""
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        cl = r.headers.get("Content-Length")
        if not cl:
            raise RuntimeError(f"Missing Content-Length for {url}")
        return int(cl)
    
    def find_latest_complete_run(
        self,
        forecast_hours: List[int],
        lookback_days: int = 7,
    ) -> Optional[Tuple[str, str]]:
        """Find the latest complete GFS run"""
        now = datetime.now(timezone.utc).date()
        
        for dback in range(0, lookback_days + 1):
            day = now - timedelta(days=dback)
            yyyymmdd = day.strftime("%Y%m%d")
            logger.debug(f"Checking date: {yyyymmdd}")
            
            for cyc in TRY_CYCLES_NEWEST_FIRST:
                # Check all required forecast hours for this run
                ok = True
                for fhr in forecast_hours:
                    _, idx_url = self.get_urls("gfs", yyyymmdd, cyc, fhr=fhr)
                    if not self.http_exists(idx_url):
                        ok = False
                        break
                
                if ok:
                    logger.info(f"Found complete run: {yyyymmdd} {cyc}Z")
                    return yyyymmdd, cyc
        
        logger.error(
            f"No complete run found within last {lookback_days} days "
            f"for hours={forecast_hours[:3]}...{forecast_hours[-3:]}"
        )
        return None
    
    def parse_idx_lines(self, idx_text: str) -> Tuple[List[int], List[str]]:
        """Parse index file to get offsets and lines"""
        offsets: List[int] = []
        lines: List[str] = []
        for line in idx_text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) < 2:
                continue
            off_str = parts[1]  # Second field is the byte offset
            if not off_str.isdigit():
                continue
            offsets.append(int(off_str))
            lines.append(line)
        offsets.sort()
        return offsets, lines
    
    def desired_offsets_wind10m(self, lines: List[str]) -> List[int]:
        """Extract offsets for 10m wind components"""
        wanted: List[int] = []
        for line in lines:
            if "10 m above ground" not in line:
                continue
            if ":UGRD:" not in line and ":VGRD:" not in line:
                continue
            parts = line.split(":", 2)
            if len(parts) >= 2 and parts[1].isdigit():
                wanted.append(int(parts[1]))  # Second field is the byte offset
        wanted.sort()
        return wanted
    
    def build_ranges_for_wanted(
        self,
        wanted_offsets: List[int],
        all_offsets: List[int],
        content_length: int
    ) -> List[Tuple[int, int]]:
        """Build byte ranges for wanted offsets"""
        ranges: List[Tuple[int, int]] = []
        for start in wanted_offsets:
            # Find the next offset in all_offsets after this start
            end = content_length - 1
            for off in all_offsets:
                if off > start:
                    end = off - 1
                    break
            ranges.append((start, end))
        return ranges
    
    def download_ranges(
        self,
        grib_url: str,
        ranges: List[Tuple[int, int]],
        out_file: Path,
        timeout: int = 180
    ):
        """Download specific byte ranges from GRIB file"""
        out_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_file.with_suffix(out_file.suffix + ".part")
        
        with open(tmp, "wb") as f:
            for (start, end) in ranges:
                logger.debug(f"Downloading bytes {start}-{end}...")
                headers = {"Range": f"bytes={start}-{end}"}
                r = requests.get(grib_url, headers=headers, stream=True, timeout=timeout)
                if r.status_code not in (200, 206):
                    r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        
        tmp.replace(out_file)
    
    def download_wind10m_subset(
        self,
        yyyymmdd: str,
        datatype: str,
        cycle: str,
        fhr: int,
        skip_if_exists: bool = True,
        throttle_seconds: float = 0.0,
    ) -> Optional[Path]:
        """Download wind 10m subset for a specific forecast hour"""

        if datatype not in ("gfs", "gdas"):
            logger.error(f"Invalid datatype: {datatype}")
            return None
        
        grib_url, idx_url = self.get_urls(datatype, yyyymmdd, cycle, fhr)
        filename = self.get_filename(datatype, yyyymmdd, cycle, fhr)
        out_file = (
            self.temp_dir
            / f"{yyyymmdd}_{cycle}Z"
            / filename
        )
        
        if skip_if_exists and out_file.exists() and out_file.stat().st_size > 0:
            logger.debug(f"File already exists: {out_file}")
            return out_file
        
        try:
            idx_text = self.fetch_text(idx_url)
            all_offsets, lines = self.parse_idx_lines(idx_text)
            wanted_offsets = self.desired_offsets_wind10m(lines)
            
            if not wanted_offsets:
                raise RuntimeError(f"No UGRD/VGRD 10m records found in {idx_url}")
            
            content_length = self.get_content_length(grib_url)
            ranges = self.build_ranges_for_wanted(wanted_offsets, all_offsets, content_length)
            
            if not ranges:
                raise RuntimeError(f"Failed to compute byte ranges for {grib_url}")
            
            self.download_ranges(grib_url, ranges, out_file)
            
            if throttle_seconds > 0:
                time.sleep(throttle_seconds)
            
            return out_file
            
        except Exception as e:
            logger.error(f"Failed to download wind data for f{fhr:03d}: {e}")
            return None
    
    def collect_historical(self, days_back: int, **kwargs) -> int:
        """
        Collect historical wind data
        
        Args:
            days_back: Number of days to go back
            
        Returns:
            Number of datasets collected
        """
        logger.info(f"Starting historical wind data collection for {days_back} days back")
        collection_id = self.db.start_collection(self.data_type)
        collected = 0
        
        try:
            # Collect data from specified days back
            target_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            yyyymmdd = target_date.strftime("%Y%m%d")
            
            
            # Download f000 (analysis time)
            fhr = 0
            datatype = "gdas"
            for cycle in TRY_CYCLES_NEWEST_FIRST:
                filename = self.get_filename(datatype, yyyymmdd, cycle, fhr)
                target_date = target_date.replace(hour=int(cycle), minute=0, second=0, microsecond=0)

                s3key = self.get_s3_key(target_date, filename)  # just to log the key format
                if self.storage.file_exists(s3key):
                    logger.info(f"Historical data already collected for {yyyymmdd} {cycle}Z f{fhr:03d}")
                    continue
                logger.info(f"Downloading historical data for {yyyymmdd} {cycle}Z f{fhr:03d}")
                
                file_path = self.download_wind10m_subset(
                    yyyymmdd=yyyymmdd,
                    datatype=datatype,
                    cycle=cycle,
                    fhr=fhr,
                    skip_if_exists=True
                )
                
                if file_path:
                    # Record this dataset
                    analysis_date = datetime.strptime(f"{yyyymmdd}{cycle}", "%Y%m%d%H")
                    analysis_date = analysis_date.replace(tzinfo=timezone.utc)
                    valid_time = analysis_date + timedelta(hours=fhr)
                    
                    success = self._record_dataset(
                        analysis_date=analysis_date,
                        cycle=cycle,
                        forecast_date=valid_time,
                        local_file_path=str(file_path),
                        is_forecast=False
                    )
                    
                    if success:
                        collected += 1
                
            self.db.complete_collection(collection_id, collected)
            logger.info(f"Historical collection completed: {collected} datasets")
            return collected
            
        except Exception as e:
            error_msg = f"Error during historical collection: {e}"
            logger.error(error_msg)
            self.db.complete_collection(collection_id, collected, error_msg)
            return collected
    
    def collect_forecast(self, forecast_hours: int, **kwargs) -> int:
        """
        Collect forecast wind data
        
        Args:
            forecast_hours: Number of forecast hours to collect
            
        Returns:
            Number of datasets collected
        """
        logger.info(f"Starting forecast wind data collection for {forecast_hours} hours")
        collection_id = self.db.start_collection(self.data_type)
        collected = 0
        
        try:
            # Generate forecast hours list (every 3 hours)
            interval_hours = config.FORECAST_INTERVAL_HOURS
            forecast_hour_list = list(range(0, forecast_hours + 1, interval_hours))
            
            # Find latest complete run
            run_info = self.find_latest_complete_run(
                forecast_hours=forecast_hour_list,
                lookback_days=7
            )
            
            if not run_info:
                raise RuntimeError("Could not find a complete GFS run")
            
            yyyymmdd, cycle = run_info
            logger.info(f"Using GFS run: {yyyymmdd} {cycle}Z")
            
            # Download each forecast hour
            for fhr in forecast_hour_list:
                logger.info(f"Downloading forecast f{fhr:03d}")
                
                file_path = self.download_wind10m_subset(
                    yyyymmdd=yyyymmdd,
                    datatype="gfs",
                    cycle=cycle,
                    fhr=fhr,
                    skip_if_exists=True,
                    throttle_seconds=0.5  # Small throttle to be nice to NOAA
                )
                
                if file_path:
                    # Record this dataset
                    forecast_date_run = datetime.strptime(f"{yyyymmdd}{cycle}", "%Y%m%d%H")
                    forecast_date_run = forecast_date_run.replace(tzinfo=timezone.utc)
                    valid_time = forecast_date_run + timedelta(hours=fhr)
                    
                    success = self._record_dataset(
                        analysis_date=forecast_date_run,
                        cycle=cycle,
                        forecast_date=valid_time,
                        local_file_path=str(file_path),
                        is_forecast=(fhr > 0)
                    )
                    
                    if success:
                        collected += 1
            
            self.db.complete_collection(collection_id, collected)
            logger.info(f"Forecast collection completed: {collected} datasets")
            return collected
            
        except Exception as e:
            error_msg = f"Error during forecast collection: {e}"
            logger.error(error_msg)
            self.db.complete_collection(collection_id, collected, error_msg)
            return collected
