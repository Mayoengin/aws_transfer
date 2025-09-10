"""
Norm API Tools for ReAct Agent
"""

import requests
from typing import Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class NormAPIConfig:
    """Configuration for Norm API access."""
    base_url: str = "https://normapi.prd.inet.telenet.be:9123"
    api_key: str = "71b1bf88-9638-11ec-96ab-005056a2b9fd"
    username: str = "mayeid"
    request_id: str = "a2c60f1428d7f083ddc9ed96b2cde79c"


class NormTools:
    """Tools for interacting with Norm API."""
    
    def __init__(self, config: NormAPIConfig = None):
        self.config = config or NormAPIConfig()
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "username": self.config.username,
            "X-Request-Id": self.config.request_id
        }
    
    def get_device_info(self, hostname: str) -> Dict[str, Any]:
        """
        Get device information from Norm API using super_search.
        
        Args:
            hostname: The device hostname to query
            
        Returns:
            Device information as dictionary
        """
        try:
            url = f"{self.config.base_url}/norm_services/v1/search/super_search"
            params = {"search_term": hostname}
            
            logger.debug(f"Fetching device info for {hostname} from {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                verify=True,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Received response with {data.get('meta', {}).get('object_count', 0)} objects")
            
            return {
                "success": True,
                "data": data,
                "hostname": hostname
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching device info for {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "hostname": hostname
            }
    
    
    
    def get_device_report(self, hostname: str, tags: list) -> Dict[str, Any]:
        """
        Get detailed device report based on device tags.
        
        Args:
            hostname: The device hostname
            tags: List of device tags to determine report type
            
        Returns:
            Detailed device report
        """
        try:
            results = {}
            
            # Convert tags to lowercase for comparison
            tags_lower = [tag.lower() for tag in tags]
            
            # Check for CE and COMWARE tags
            if 'ce' in tags_lower and 'comware' in tags_lower:
                logger.info(f"Fetching Comware CE device report for {hostname}")
                url = f"{self.config.base_url}/norm_services/v1/view/comware/{hostname}/detail"
                
                response = requests.get(
                    url,
                    headers=self.headers,
                    verify=True,
                    timeout=30
                )
                
                response.raise_for_status()
                results['comware_detail'] = response.json()
                results['report_type'] = 'comware_ce'
                
            # Check for TIMOS and CORE tags
            elif 'timos' in tags_lower and 'core' in tags_lower:
                logger.info(f"Fetching TIMOS Core device report for {hostname}")
                
                # Fetch multiple endpoints for TIMOS Core devices
                endpoints = [
                    ('saps', f"/norm_services/v1/view/timos/{hostname}/saps"),
                    ('routes', f"/norm_services/v1/view/timos/{hostname}/routes"),
                    ('device_info', f"/devicemanager/v1/device?hostname=^{hostname}$"),
                    ('subscribers', f"/norm_services/v1/view/timos/{hostname}/subscribers"),
                    ('interfaces', f"/norm_services/v1/view/timos/{hostname}/interfaces")
                ]
                
                for endpoint_name, endpoint_path in endpoints:
                    try:
                        url = f"{self.config.base_url}{endpoint_path}"
                        
                        # Use different headers for devicemanager endpoint
                        if 'devicemanager' in endpoint_path:
                            headers = self.headers.copy()
                            headers['key'] = headers.pop('x-api-key', self.config.api_key)
                        else:
                            headers = self.headers
                        
                        response = requests.get(
                            url,
                            headers=headers,
                            verify=True,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            results[endpoint_name] = response.json()
                        else:
                            logger.warning(f"Failed to fetch {endpoint_name}: {response.status_code}")
                            results[endpoint_name] = {"error": f"HTTP {response.status_code}"}
                            
                    except Exception as e:
                        logger.error(f"Error fetching {endpoint_name}: {e}")
                        results[endpoint_name] = {"error": str(e)}
                
                results['report_type'] = 'timos_core'
            
            else:
                # Generic report for other device types
                logger.info(f"No specific report type for tags: {tags}")
                return {
                    "success": False,
                    "error": f"No specific report available for device with tags: {', '.join(tags)}",
                    "hostname": hostname
                }
            
            return {
                "success": True,
                "data": results,
                "hostname": hostname,
                "tags": tags
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching device report for {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "hostname": hostname
            }


def get_available_tools():
    """Get list of available tool descriptions for the agent."""
    return [
        {
            "name": "get_device_info",
            "description": "Retrieve detailed information about a network device including its configuration, status, and properties",
            "parameters": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "The hostname of the device to query (e.g., CEAWPDGA05)"
                    }
                },
                "required": ["hostname"]
            }
        },
        {
            "name": "get_device_report",
            "description": "Get a detailed report for a device based on its type (determined by tags). For CE+COMWARE devices, fetches Comware details. For TIMOS+CORE devices, fetches SAPs, routes, subscribers, and interfaces.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "The hostname of the device"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of device tags (e.g., ['CE', 'COMWARE'] or ['TIMOS', 'CORE'])"
                    }
                },
                "required": ["hostname", "tags"]
            }
        }
    ]