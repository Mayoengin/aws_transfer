"""
get_device_report tool implementation with data interpretation guide
"""

import requests
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class GetDeviceReport:
    """Tool for retrieving detailed device reports based on device type."""
    
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "username": self.config.username,
            "X-Request-Id": self.config.request_id
        }
    
    @property
    def prompt(self) -> str:
        """System prompt explaining how to use and interpret this tool."""
        return """
        TOOL: get_device_report
        PURPOSE: Retrieves detailed device report based on device type (TIMOS or COMWARE)
        
        WHEN TO USE THIS TOOL:
        - ONLY when user explicitly asks for "detailed report" or "full details"
        - ONLY when user responds "yes" after you offered a detailed report
        - NEVER call this automatically after get_device_info
        
        IMPORTANT: You must first identify the device type from tags before calling this tool:
        - TIMOS devices: Use tags ["TIMOS", "CORE"]
        - COMWARE devices: Use tags ["CE", "COMWARE"]
        
        DATA STRUCTURE FOR TIMOS DEVICES:
        {
            "system_info": {
                "hostname": device name,
                "model": hardware model,
                "version": software version,
                "uptime": system uptime
            },
            "interfaces": [...interface details],
            "services": {
                "vpls": [...VPLS services],
                "vprn": [...VPRN services],
                "ies": [...IES services]
            },
            "alarms": [...active alarms]
        }
        
        DATA STRUCTURE FOR COMWARE DEVICES:
        {
            "device_info": {
                "hostname": device name,
                "model": hardware model,
                "version": software version,
                "location": physical location
            },
            "interfaces": [...interface configurations],
            "vlans": [...VLAN configurations],
            "routing": {...routing information}
        }
        
        HOW TO DISPLAY RESULTS:
        1. First show system overview:
           - Hostname and model
           - Software version
           - Uptime (for TIMOS) or Location (for COMWARE)
        
        2. Then summarize key metrics:
           - Total interfaces and their status (up/down count)
           - Number of services (for TIMOS) or VLANs (for COMWARE)
           - Any critical alarms or issues
        
        3. Offer to drill down into specific areas
        
        EXAMPLE RESPONSE FOR TIMOS:
        "SRMECH01 - Nokia 7750 SR Router
        Software: TiMOS-B-20.10.R1
        Uptime: 365 days, 12 hours
        
        Status Summary:
        - Interfaces: 45 total (40 up, 5 down)
        - Services: 25 active (10 VPLS, 10 VPRN, 5 IES)
        - Alarms: 2 minor, 0 critical
        
        Would you like details on interfaces, services, or alarms?"
        
        EXAMPLE RESPONSE FOR COMWARE:
        "CEAWPDGA05 - H3C S5820 Switch
        Software: Comware V7.1.070
        Location: Data Center A, Rack 15
        
        Configuration Summary:
        - Interfaces: 24 total (20 up, 4 down)
        - VLANs: 15 configured
        - Routing: OSPF and BGP enabled
        
        Need details on interfaces, VLANs, or routing?"
        
        ERROR HANDLING:
        - 409 Conflict: Wrong device type - try different tags
        - 404 Not Found: Device doesn't exist or not in this category
        - 500 Server Error: API issue, retry or check device name
        """
    
    def execute(self, hostname: str, tags: List[str]) -> Dict[str, Any]:
        """
        Execute the tool to get detailed device report.
        
        Args:
            hostname: The device hostname
            tags: List of device tags to determine report type
            
        Returns:
            Detailed device report with success status
        """
        try:
            results = {}
            
            # Convert tags to lowercase for comparison
            tags_lower = [tag.lower() for tag in tags]
            
            # Determine device type and construct URL
            if 'ce' in tags_lower and 'comware' in tags_lower:
                logger.info(f"Fetching Comware CE device report for {hostname}")
                url = f"{self.config.base_url}/norm_services/v1/view/comware/{hostname}/detail"
                device_type = "COMWARE"
            elif 'timos' in tags_lower and 'core' in tags_lower:
                logger.info(f"Fetching TIMOS Core device report for {hostname}")
                url = f"{self.config.base_url}/norm_services/v1/view/timos/{hostname}/detail"
                device_type = "TIMOS"
            else:
                return {
                    "success": False,
                    "error": f"Unknown device type for tags: {tags}. Use ['TIMOS', 'CORE'] or ['CE', 'COMWARE']",
                    "hostname": hostname
                }
            
            response = requests.get(
                url,
                headers=self.headers,
                verify=True,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "data": data,
                "hostname": hostname,
                "device_type": device_type
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                error_msg = f"Device type mismatch for {hostname}. Try different tags: ['TIMOS', 'CORE'] or ['CE', 'COMWARE']"
            elif e.response.status_code == 404:
                error_msg = f"Device {hostname} not found in the {device_type if 'device_type' in locals() else 'specified'} category"
            else:
                error_msg = f"HTTP Error {e.response.status_code}: {str(e)}"
            
            logger.error(f"Error fetching device report for {hostname}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "hostname": hostname
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching device report for {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "hostname": hostname
            }
    
    def interpret_response(self, result: Dict[str, Any]) -> str:
        """
        Interpret the tool response for display.
        
        Args:
            result: The raw result from execute()
            
        Returns:
            Human-readable interpretation
        """
        if not result["success"]:
            return f"Failed to get device report: {result.get('error', 'Unknown error')}"
        
        data = result.get("data", {})
        hostname = result.get("hostname", "Unknown")
        device_type = result.get("device_type", "Unknown")
        
        if device_type == "TIMOS":
            return self._format_timos_report(hostname, data)
        elif device_type == "COMWARE":
            return self._format_comware_report(hostname, data)
        else:
            return f"Received report for {hostname} but unable to determine format"
    
    def _format_timos_report(self, hostname: str, data: Dict) -> str:
        """Format TIMOS device report."""
        system_info = data.get("system_info", {})
        interfaces = data.get("interfaces", [])
        services = data.get("services", {})
        alarms = data.get("alarms", [])
        
        # Count interface status
        up_count = sum(1 for i in interfaces if i.get("status") == "up")
        down_count = len(interfaces) - up_count
        
        # Count services
        vpls_count = len(services.get("vpls", []))
        vprn_count = len(services.get("vprn", []))
        ies_count = len(services.get("ies", []))
        total_services = vpls_count + vprn_count + ies_count
        
        # Count alarms by severity
        critical_alarms = sum(1 for a in alarms if a.get("severity") == "critical")
        minor_alarms = sum(1 for a in alarms if a.get("severity") == "minor")
        
        response = f"{hostname} - {system_info.get('model', 'Nokia Router')}\n"
        response += f"Software: {system_info.get('version', 'Unknown')}\n"
        response += f"Uptime: {system_info.get('uptime', 'Unknown')}\n\n"
        response += f"Status Summary:\n"
        response += f"- Interfaces: {len(interfaces)} total ({up_count} up, {down_count} down)\n"
        response += f"- Services: {total_services} active ({vpls_count} VPLS, {vprn_count} VPRN, {ies_count} IES)\n"
        response += f"- Alarms: {minor_alarms} minor, {critical_alarms} critical\n\n"
        response += "Would you like details on interfaces, services, or alarms?"
        
        return response
    
    def _format_comware_report(self, hostname: str, data: Dict) -> str:
        """Format COMWARE device report."""
        device_info = data.get("device_info", {})
        interfaces = data.get("interfaces", [])
        vlans = data.get("vlans", [])
        routing = data.get("routing", {})
        
        # Count interface status
        up_count = sum(1 for i in interfaces if i.get("status") == "up")
        down_count = len(interfaces) - up_count
        
        response = f"{hostname} - {device_info.get('model', 'H3C Switch')}\n"
        response += f"Software: {device_info.get('version', 'Unknown')}\n"
        response += f"Location: {device_info.get('location', 'Unknown')}\n\n"
        response += f"Configuration Summary:\n"
        response += f"- Interfaces: {len(interfaces)} total ({up_count} up, {down_count} down)\n"
        response += f"- VLANs: {len(vlans)} configured\n"
        
        # Add routing protocols if present
        protocols = []
        if routing.get("ospf"):
            protocols.append("OSPF")
        if routing.get("bgp"):
            protocols.append("BGP")
        if protocols:
            response += f"- Routing: {', '.join(protocols)} enabled\n"
        
        response += "\nNeed details on interfaces, VLANs, or routing?"
        
        return response