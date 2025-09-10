"""
Formatting utilities for ReAct Agent responses
"""

import json
from typing import Dict, Any


class ResponseFormatter:
    """Handles all response formatting for the ReAct agent."""
    
    def format_observation(self, result: Dict[str, Any]) -> str:
        """Format tool result into a human-readable observation."""
        if not result.get("success"):
            return f"Failed to retrieve data: {result.get('error')}"
        
        data = result.get("data", {})
        
        # Handle device report response
        if isinstance(data, dict) and "report_type" in data:
            return self.format_device_report(data)
        
        # Handle super_search response format
        if isinstance(data, dict) and "data" in data:
            return self.format_super_search_response(data)
        
        if isinstance(data, list):
            if len(data) == 0:
                return "No devices found matching the criteria."
            
            observations = []
            for device in data[:5]:  # Limit to first 5 devices
                device_info = self.format_device_data(device)
                observations.append(device_info)
            
            observation = "\n".join(observations)
            if len(data) > 5:
                observation += f"\n... and {len(data) - 5} more devices"
            
            return observation
        else:
            return self.format_device_data(data)
    
    def format_super_search_response(self, response: Dict[str, Any]) -> str:
        """Format super_search API response into readable observation."""
        items = response.get("data", [])
        
        if not items:
            return "No results found for the search term."
        
        # Group items by type
        device_info = None
        interfaces = []
        network_info = None
        chassis_info = None
        connections = []
        
        for item in items:
            classname = item.get("classname", "")
            identifier = item.get("identifier", "")
            additional_info = item.get("additional_info", [])
            origin = item.get("origin", "")
            
            if classname == "NormDevice":
                device_info = {
                    "hostname": identifier,
                    "tags": [tag for tag in additional_info if tag != identifier]
                }
            elif classname == "Network":
                network_info = {
                    "ip": additional_info[1] if len(additional_info) > 1 else "N/A",
                    "fqdn": additional_info[2] if len(additional_info) > 2 else "N/A",
                    "customer": additional_info[3] if len(additional_info) > 3 else "N/A"
                }
            elif classname in ["ComwareInterface", "TimosVrtrInterface"]:
                interfaces.append({
                    "name": identifier,
                    "device": origin,
                    "type": classname
                })
            elif classname == "ComwareEntPhysical" and item.get("groupname") == "Chassis":
                chassis_info = {
                    "model": additional_info[1] if len(additional_info) > 1 else "Unknown"
                }
            elif classname == "TimosSap":
                if len(additional_info) >= 9:
                    connections.append({
                        "sap": identifier,
                        "router": origin,
                        "service": additional_info[3] if len(additional_info) > 3 else "N/A",
                        "vlan": additional_info[8] if len(additional_info) > 8 else "N/A"
                    })
        
        # Build formatted output with better visual structure
        output = []
        
        if device_info:
            output.append("┌─ 📡 DEVICE OVERVIEW")
            output.append(f"│  Device Name: {device_info['hostname']}")
            if chassis_info:
                output.append(f"│  Model: {chassis_info['model']}")
            if device_info['tags']:
                output.append(f"│  Tags: {', '.join(device_info['tags'])}")
            output.append("└─")
        
        if network_info:
            output.append("\n┌─ 🌐 NETWORK INFORMATION")
            output.append(f"│  IP Address: {network_info['ip']}")
            output.append(f"│  FQDN: {network_info['fqdn']}")
            output.append(f"│  Customer: {network_info['customer']}")
            output.append("└─")
        
        if interfaces:
            output.append(f"\n┌─ 🔌 INTERFACES ({len(interfaces)} found)")
            for intf in interfaces[:6]:  # Show first 6 interfaces
                output.append(f"│  • {intf['name']}")
            if len(interfaces) > 6:
                output.append(f"│  ... and {len(interfaces) - 6} more")
            output.append("└─")
        
        if connections:
            output.append("\n┌─ 🔗 NETWORK CONNECTIONS")
            for conn in connections:
                output.append(f"│  Upstream Router: {conn['router']}")
                output.append(f"│  Service: {conn['service']}")
                output.append(f"│  SAP: {conn['sap']} (VLAN {conn['vlan']})")
            output.append("└─")
        
        meta = response.get("meta", {})
        if meta:
            output.append(f"\n📊 Query completed in {meta.get('query_duration', 'N/A')} - {meta.get('object_count', 'N/A')} objects found")
        
        return "\n".join(output)
    
    def format_device_report(self, data: Dict[str, Any]) -> str:
        """Format device report based on report type."""
        report_type = data.get("report_type")
        output = []
        
        if report_type == "comware_ce":
            output.append("📋 COMWARE CE DEVICE DETAILED REPORT")
            output.append("=" * 60)
            
            detail = data.get("comware_detail", {})
            if detail:
                # Format device basic info
                if "hostname" in detail:
                    output.append(f"\n🔹 Device: {detail.get('hostname')}")
                if "model" in detail:
                    output.append(f"🔹 Model: {detail.get('model')}")
                if "vendor" in detail:
                    output.append(f"🔹 Vendor: {detail.get('vendor')}")
                
                # Format interfaces
                if "interfaces" in detail:
                    output.append("\n📡 INTERFACES:")
                    output.append("-" * 40)
                    interfaces = detail.get("interfaces", [])
                    if isinstance(interfaces, list):
                        for intf in interfaces[:10]:
                            if isinstance(intf, dict):
                                name = intf.get("name", "Unknown")
                                status = intf.get("status", "Unknown")
                                ip = intf.get("ip_address", "N/A")
                                output.append(f"  • {name}: {status} (IP: {ip})")
                            else:
                                output.append(f"  • {intf}")
                        if len(interfaces) > 10:
                            output.append(f"  ... and {len(interfaces) - 10} more interfaces")
                    else:
                        output.append(f"  {interfaces}")
                
                # Format VRF information
                if "vrfs" in detail:
                    output.append("\n🌐 VRF CONFIGURATION:")
                    output.append("-" * 40)
                    vrfs = detail.get("vrfs", {})
                    if isinstance(vrfs, dict):
                        for vrf_name, vrf_data in list(vrfs.items())[:5]:
                            output.append(f"  VRF: {vrf_name}")
                            if isinstance(vrf_data, dict):
                                if "interfaces" in vrf_data:
                                    output.append(f"    Interfaces: {', '.join(vrf_data['interfaces'][:3])}")
                                if "routes" in vrf_data:
                                    output.append(f"    Routes: {len(vrf_data.get('routes', []))} configured")
                
                # Format last discovered information
                if "last_discovered" in detail:
                    output.append("\n🕒 LAST DISCOVERED:")
                    output.append("-" * 40)
                    last_disc = detail.get("last_discovered")
                    if isinstance(last_disc, dict):
                        for key, value in last_disc.items():
                            output.append(f"  {key}: {value}")
                    else:
                        output.append(f"  {last_disc}")
                
                # Format CPE details
                if "cpe_details" in detail:
                    output.append("\n🔧 CPE DETAILS:")
                    output.append("-" * 40)
                    cpe = detail.get("cpe_details", {})
                    if isinstance(cpe, dict):
                        for key, value in cpe.items():
                            output.append(f"  {key}: {value}")
                
                # Format any additional data
                for key in detail:
                    if key not in ["hostname", "model", "vendor", "interfaces", "vrfs", "last_discovered", "cpe_details"]:
                        output.append(f"\n📌 {key.upper().replace('_', ' ')}:")
                        output.append("-" * 40)
                        value = detail[key]
                        if isinstance(value, (dict, list)):
                            output.append(f"  {json.dumps(value, indent=2)[:300]}")
                        else:
                            output.append(f"  {value}")
            
        elif report_type == "timos_core":
            output.append("📋 TIMOS CORE DEVICE DETAILED REPORT")
            output.append("=" * 60)
            
            # DEBUG: Show what data keys we have
            output.append(f"\n🔍 DEBUG - Available data keys: {list(data.keys())}")
            
            # Format Device Info first
            if "device_info" in data:
                dev_data = data.get("device_info", {})
                output.append(f"\n📡 DEVICE INFORMATION:")
                output.append("-" * 40)
                output.append(f"  DEBUG - device_info type: {type(dev_data)}")
                output.append(f"  DEBUG - device_info keys: {list(dev_data.keys()) if isinstance(dev_data, dict) else 'Not a dict'}")
                
                if isinstance(dev_data, dict) and "data" in dev_data:
                    device_list = dev_data.get("data", [])
                    if device_list:
                        device = device_list[0] if isinstance(device_list, list) else device_list
                        output.append(f"  Hostname: {device.get('hostname', 'N/A')}")
                        output.append(f"  Platform: {device.get('platform', 'N/A')}")
                        output.append(f"  Room: {device.get('room', 'N/A')}")
                        output.append(f"  Rack Location: {device.get('rack_location', 'N/A')}")
                        output.append(f"  Tags: {', '.join(device.get('tags', []))}")
                elif isinstance(dev_data, dict):
                    for key, value in dev_data.items():
                        if key != "error":
                            output.append(f"  {key}: {value}")
                else:
                    output.append(f"  Raw data: {dev_data}")
            
            # Format SAPs with details
            if "saps" in data:
                saps_data = data.get("saps", {})
                output.append("\n🔗 SERVICE ACCESS POINTS (SAPs):")
                output.append("-" * 40)
                output.append(f"  DEBUG - saps type: {type(saps_data)}")
                output.append(f"  DEBUG - saps keys: {list(saps_data.keys()) if isinstance(saps_data, dict) else 'Not a dict'}")
                
                if isinstance(saps_data, dict) and "data" in saps_data:
                    sap_list = saps_data.get("data", [])
                    if sap_list:
                        output.append(f"  Total SAPs: {len(sap_list)}")
                        for i, sap in enumerate(sap_list[:5], 1):
                            output.append(f"  {i}. {sap}")
                    else:
                        output.append("  No SAPs found")
                elif not isinstance(saps_data, dict) or not saps_data.get("error"):
                    if isinstance(saps_data, list):
                        output.append(f"  Total SAPs: {len(saps_data)}")
                        for i, sap in enumerate(saps_data[:5], 1):
                            output.append(f"  {i}. {sap}")
                    else:
                        output.append(f"  Raw SAPs data: {saps_data}")
                else:
                    output.append(f"  SAPs Error: {saps_data.get('error')}")
            
            # Format Routes with summary
            if "routes" in data:
                routes_data = data.get("routes", {})
                output.append("\n🛤️ ROUTING INFORMATION:")
                output.append("-" * 40)
                output.append(f"  DEBUG - routes type: {type(routes_data)}")
                output.append(f"  DEBUG - routes keys: {list(routes_data.keys()) if isinstance(routes_data, dict) else 'Not a dict'}")
                
                if isinstance(routes_data, dict) and "data" in routes_data:
                    route_list = routes_data.get("data", [])
                    output.append(f"  Total Routes: {len(route_list)}")
                    for route in route_list[:5]:
                        output.append(f"    • {route}")
                elif isinstance(routes_data, dict) and not routes_data.get("error"):
                    output.append(f"  Raw routes data: {routes_data}")
                else:
                    output.append(f"  Routes data: {routes_data}")
            
            # Format Interfaces with details
            if "interfaces" in data:
                intf_data = data.get("interfaces", {})
                output.append("\n🔌 NETWORK INTERFACES:")
                output.append("-" * 40)
                output.append(f"  DEBUG - interfaces type: {type(intf_data)}")
                output.append(f"  DEBUG - interfaces keys: {list(intf_data.keys()) if isinstance(intf_data, dict) else 'Not a dict'}")
                
                if isinstance(intf_data, dict) and "data" in intf_data:
                    intf_list = intf_data.get("data", [])
                    output.append(f"  Total Interfaces: {len(intf_list)}")
                    for intf in intf_list[:5]:
                        output.append(f"    • {intf}")
                elif isinstance(intf_data, list):
                    output.append(f"  Total Interfaces: {len(intf_data)}")
                    for intf in intf_data[:5]:
                        output.append(f"    • {intf}")
                else:
                    output.append(f"  Interfaces data: {intf_data}")
            
            # Format Subscribers
            if "subscribers" in data:
                sub_data = data.get("subscribers", {})
                output.append("\n👥 SUBSCRIBER INFORMATION:")
                output.append("-" * 40)
                output.append(f"  DEBUG - subscribers type: {type(sub_data)}")
                output.append(f"  DEBUG - subscribers keys: {list(sub_data.keys()) if isinstance(sub_data, dict) else 'Not a dict'}")
                
                if isinstance(sub_data, dict) and "data" in sub_data:
                    sub_list = sub_data.get("data", [])
                    output.append(f"  Total Subscribers: {len(sub_list)}")
                    for sub in sub_list[:5]:
                        output.append(f"    • {sub}")
                elif isinstance(sub_data, list):
                    output.append(f"  Total Subscribers: {len(sub_data)}")
                    for sub in sub_data[:5]:
                        output.append(f"    • {sub}")
                else:
                    output.append(f"  Subscribers data: {sub_data}")
        
        return "\n".join(output)
    
    def format_device_data(self, device: Dict[str, Any]) -> str:
        """Format individual device data."""
        formatted_parts = []
        
        # Extract key information
        hostname = device.get("hostname", "Unknown")
        ip = device.get("management_ip", device.get("ip_address", "N/A"))
        vendor = device.get("vendor", "Unknown")
        model = device.get("model", device.get("device_type", "Unknown"))
        status = device.get("status", device.get("operational_status", "Unknown"))
        location = device.get("location", device.get("site", "N/A"))
        
        formatted_parts.append(f"Device: {hostname}")
        formatted_parts.append(f"  - IP: {ip}")
        formatted_parts.append(f"  - Vendor/Model: {vendor} {model}")
        formatted_parts.append(f"  - Status: {status}")
        
        if location != "N/A":
            formatted_parts.append(f"  - Location: {location}")
        
        # Add any interfaces info if present
        if "interfaces" in device:
            interface_count = len(device["interfaces"])
            formatted_parts.append(f"  - Interfaces: {interface_count} total")
        
        return "\n".join(formatted_parts)