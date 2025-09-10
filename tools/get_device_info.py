"""
get_device_info tool implementation with data interpretation guide
"""

import requests
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class GetDeviceInfo:
    """Tool for retrieving device information from NORM super_search endpoint."""
    
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
        TOOL: get_device_info
        PURPOSE: Retrieves comprehensive network device information from NORM super_search endpoint
        
        DATA STRUCTURE RETURNED:
        The API returns a complex dataset with multiple object types. Each object has:
        {
            "classname": object type (see types below),
            "identifier": unique ID or name,
            "origin": source device (usually the queried device),
            "additional_info": array with detailed information,
            "groupname": logical grouping,
            "result_id": unique result identifier
        }
        
        OBJECT TYPES AND MEANINGS:
        
        DEVICE IDENTITY (1 record):
        - NormDevice: Main device record with type, role, location tags
        - TimosChassis: Physical hardware info (model, capabilities)
        - ConsolePort: Management access points for administrators
        
        NETWORK COMPONENTS:
        - TimosVrtrInterface: Virtual router interfaces (Layer 3, customer connections)
        - JunosInterface: Juniper device interfaces (if connected)  
        - Interface: Generic network interfaces
        AGGREGATE AS: "Interfaces" 
        
        SERVICE ACCESS POINTS:
        - Sap: Standard service access points (customer connection endpoints)
        - TimosSap: Nokia TIMOS-specific SAPs
        AGGREGATE AS: "SAPs"
        
        PHYSICAL INFRASTRUCTURE:
        - TimosPort: Physical network ports on the device
        - Port: Generic physical ports
        AGGREGATE AS: "Ports"
        
        SERVICES & CONNECTIVITY:
        - TimosService: Active network services (VPNs, VPLS, etc.)
        - TimosLag: Link Aggregation Groups (redundancy/bandwidth)
        - Network: IP networks and subnets managed by device
        - TimosSatellite: Remote extension devices managed by main device
        
        HOW TO DISPLAY RESULTS:
        
        1. DEVICE HEADER (extract from NormDevice and TimosChassis):
        🖥️ [HOSTNAME] - [Hardware Model] ([Device Type])
           Location: [Location from tags]
           Role: [Role tags like CORE, RESIDENTIAL]
        
        2. AGGREGATE COMPONENT SUMMARY:
        📊 Network Components:
           • XXX Interfaces (all interface types combined)
           • XXX SAPs - Service Access Points (all SAP types combined)  
           • XXX Services (active network services)
           • XXX Ports (all port types combined)
           • XX Link Aggregation Groups
           • XX Networks (IP subnets)
           • X Satellite Devices (if any)
        
        3. KEY CONNECTIONS (extract from objects with different origins):
        🔗 Connected Devices:
           • [Connected Device 1]
           • [Connected Device 2] 
           • [etc...]
        
        4. MANAGEMENT INFO (extract from Network objects):
        🌍 Management Networks:
           • [Management IP 1]
           • [Management IP 2]
        
        5. END WITH OFFER:
        Would you like a detailed report for this device?
        
        EXAMPLE FINAL ANSWER FORMAT:
        🖥️ [HOSTNAME] - [Hardware Model] ([Device Type])
           Location: [Extract from device tags]  
           Role: [Extract role tags from device info]
        
        📊 Network Components:
           • [COUNT] Interfaces (customer/service connections)
           • [COUNT] SAPs - Service Access Points  
           • [COUNT] Active Services
           • [COUNT] Physical Ports
           • [COUNT] Link Aggregation Groups
           • [COUNT] IP Networks
           • [COUNT] Satellite Devices (if any)
        
        🔗 Connected Devices:
           • [Device Name] ([relationship/purpose])
           • [Device Name] ([relationship/purpose])
           • + [N] other devices
        
        🌍 Management Networks:
           • [Management IP 1], [Management IP 2]
           • [Loopback IP] (main loopback)
        
        Would you like a detailed report for this device?
        
        CRITICAL RULES:
        - AGGREGATE similar object types (don't show individual counts)
        - Extract meaningful information from additional_info arrays
        - Show DEVICE PURPOSE, not just component counts
        - This should be your FINAL ANSWER - do not call other tools
        - Present data that helps users understand what the device does
        """
    
    def execute(self, hostname: str) -> Dict[str, Any]:
        """
        Execute the tool to get device information.
        
        Args:
            hostname: The device hostname to query
            
        Returns:
            Device information with success status
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
    
    def interpret_response(self, result: Dict[str, Any]) -> str:
        """
        Interpret the tool response for display.
        
        Args:
            result: The raw result from execute()
            
        Returns:
            Human-readable interpretation
        """
        if not result["success"]:
            return f"Failed to get device info: {result.get('error', 'Unknown error')}"
        
        data = result.get("data", {})
        objects = data.get("data", [])  # API returns objects in 'data' array
        hostname = result.get("hostname", "Unknown")
        
        if not objects:
            return f"No data found for device {hostname}"
        
        # Parse device identity
        device_record = None
        chassis_record = None
        for obj in objects:
            if obj.get("classname") == "NormDevice":
                device_record = obj
            elif obj.get("classname") == "TimosChassis":
                chassis_record = obj
        
        # Extract device info
        device_type = "Unknown Device"
        location = "Unknown Location"
        role = "Unknown Role"
        hardware_model = "Unknown Model"
        
        if device_record:
            tags = device_record.get("additional_info", [])
            # Extract device type
            if "TIMOS" in tags and "SR" in tags:
                device_type = "TIMOS Service Router"
            # Extract location
            location_tags = [tag for tag in tags if "HE_" in tag or "MECH" in tag]
            if location_tags:
                location = " ".join(location_tags).replace("HE_", "Head-End ").replace("_", " ")
            # Extract role
            role_tags = [tag for tag in tags if tag in ["CORE", "RESIDENTIAL", "BSOD", "EDGE"]]
            if role_tags:
                role = " | ".join(role_tags)
        
        if chassis_record:
            chassis_info = chassis_record.get("additional_info", [])
            if chassis_info:
                hardware_model = chassis_info[0]
        
        # Count aggregated components
        interface_types = ['TimosVrtrInterface', 'JunosInterface', 'Interface']
        sap_types = ['Sap', 'TimosSap']
        port_types = ['TimosPort', 'Port']
        
        interfaces = sum(len([obj for obj in objects if obj.get("classname") == t]) for t in interface_types)
        saps = sum(len([obj for obj in objects if obj.get("classname") == t]) for t in sap_types)
        services = len([obj for obj in objects if obj.get("classname") == "TimosService"])
        ports = sum(len([obj for obj in objects if obj.get("classname") == t]) for t in port_types)
        lags = len([obj for obj in objects if obj.get("classname") == "TimosLag"])
        networks = len([obj for obj in objects if obj.get("classname") == "Network"])
        satellites = len([obj for obj in objects if obj.get("classname") == "TimosSatellite"])
        
        # Find connected devices
        connected_devices = set()
        for obj in objects:
            origin = obj.get("origin")
            if origin and origin != hostname and origin not in [None, "None"]:
                connected_devices.add(origin)
        
        # Find management networks
        mgmt_networks = []
        loopback_ip = None
        for obj in objects:
            if obj.get("classname") == "Network":
                identifier = obj.get("identifier", "")
                ip = identifier.replace("default/", "")
                additional_info = obj.get("additional_info", [])
                
                # Check if it's a management network
                if any(hostname in str(info) for info in additional_info):
                    if "LOOPBACK" in " ".join(map(str, additional_info)).upper():
                        loopback_ip = ip
                    else:
                        mgmt_networks.append(ip)
        
        # Build formatted response
        response = f"🖥️ {hostname} - {hardware_model} ({device_type})\n"
        response += f"   Location: {location}\n"
        response += f"   Role: {role}\n\n"
        
        response += f"📊 Network Components:\n"
        response += f"   • {interfaces} Interfaces (customer/service connections)\n"
        response += f"   • {saps} SAPs - Service Access Points\n"
        response += f"   • {services} Active Services\n"
        response += f"   • {ports} Physical Ports\n"
        response += f"   • {lags} Link Aggregation Groups\n"
        response += f"   • {networks} IP Networks\n"
        if satellites > 0:
            response += f"   • {satellites} Satellite Devices\n"
        response += f"\n"
        
        if connected_devices:
            response += f"🔗 Connected Devices:\n"
            # Show first few connected devices
            for device in sorted(list(connected_devices))[:3]:
                response += f"   • {device}\n"
            if len(connected_devices) > 3:
                response += f"   • + {len(connected_devices) - 3} other devices\n"
            response += f"\n"
        
        if mgmt_networks or loopback_ip:
            response += f"🌍 Management Networks:\n"
            if mgmt_networks:
                response += f"   • {', '.join(mgmt_networks[:2])}\n"
            if loopback_ip:
                response += f"   • {loopback_ip} (main loopback)\n"
            response += f"\n"
        
        response += "Would you like a detailed report for this device?"
        
        return response