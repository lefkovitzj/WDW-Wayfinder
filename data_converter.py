"""
Project Name: WDW-Wayfinder
File Name: data_converter.py
Description: Data JSON generation and conversion utility.
Author: Joseph Lefkovitz (github.com/lefkovitzj)
Last Modified: 3/13/2026
"""

# Standard library imports
import json
import re

# Local imports
from data.raw_data import (
    mapping,
    monorails,
    boats,
    skyliners,
    walks,
    manual_busses,
    bus_sources,
    bus_destinations,
    bus_only,
    no_bus_nodes,
    internal_bus_loops
)

def lookup_id(id, mapping=mapping):
    """Helper function to map ID to long strings."""
    for name, mapped_id in mapping.items():
        if mapped_id == id:
            return name
    return id


def _norm_suffix(text: str) -> str:
    """Normalize a stop suffix into an ID-safe token."""
    return re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")

def clean_id(name, mapping=mapping):
    """Maps long strings to standardized Sub-node IDs."""

    # Check for direct matches first
    if name in mapping:
        return mapping[name]

    # Handle internal bus loop stops: "Resort Name (Stop Name)"
    if "(" in name and ")" in name:
        resort_part = name.split("(", 1)[0].strip()
        stop_part = name.split("(", 1)[1].split(")", 1)[0].strip()
        if resort_part in mapping:
                resort_id = mapping[resort_part]
                stop_id = stop_part.replace(" ", "_").upper()
                print(f"Mapped internal bus loop stop: {name} -> {resort_id}_{stop_id}")
                return f"{resort_id}_{stop_id}"

    # Process suffixes for transit sub-nodes
    parts = name.split(" - ", 1)
    base = parts[0].replace("(", "").replace(")", "").strip()
    suffix = parts[1] if len(parts) > 1 else ""
    base_id = mapping.get(base, base.replace(" ", "_").upper())

    if "Resort Monorail" in name:
        return base_id + "_RMON"
    if "Express Monorail" in name:
        return base_id + "_EMON"
    if "Epcot Monorail" in name:
        return base_id + "_EPMON"
    if "Skyliner" in name:
        return base_id + "_SKY"

    # IMPORTANT: keep boat stops distinct by suffix (e.g. ...TO_EPCOT vs ...TO_HOLLYWOOD_STUDIOS)
    if "Launch" in name or "Boat" in name or "Ferry" in name:
        if suffix:
            return f"{base_id}_{_norm_suffix(suffix)}"
        return base_id + "_BOAT"

    return base_id

def has_premium_transit(resort_id, park_id, connections, no_bus_nodes=no_bus_nodes, mapping=mapping, display_names={}):
    """Checks if the resort has any incident premium-transit edge."""
    display_names.update(mapping)
    reverse_display_names = {v: k for k, v in display_names.items()}

    park_name = reverse_display_names[park_id]
    resort_name = reverse_display_names[resort_id]
    if (resort_name, park_name) in no_bus_nodes:
        return True
    return False

def insert_bus_display_names(final_data):
    """  Insert display names for bus nodes based on existing display names. """
    for bus_source in bus_sources:
        bus_source_id = clean_id(bus_source)
        bus_source_stop_id = f"{bus_source_id}_BUS"
        final_data["display_names"][bus_source] = bus_source_id
        final_data["display_names"][f"{bus_source} - Bus Stop"] = bus_source_stop_id

    for bus_destination in bus_destinations:
        bus_destination_id = clean_id(bus_destination)
        bus_destination_stop_id = f"{bus_destination_id}_BUS"
        final_data["display_names"][bus_destination] = bus_destination_id
        final_data["display_names"][f"{bus_destination} - Bus Stop"] = bus_destination_stop_id


def generate_busses(final_data, manual_busses, internal_bus_loops):
    """ Dynamically create bus routes based on existing data. """
    bus_connections = []

    # One-time creation of busses at hubs. 
    internal_stops = []
    for bus_route in internal_bus_loops:
        internal_stops.append(bus_route["resort"])
    for hub, weight in bus_destinations.items():
        if hub in internal_stops:
            continue
        # No Disney busses offered to/from TTC hub, but create it anyway.
        hub_id = clean_id(hub)
        hub_bus = hub_id+ "_BUS"
        bus_connections.append({
            "from": hub_bus, "to": hub_id, "weight": 5, "mode": "Walk", "bidirectional": False
        })
        bus_connections.append({
            "from": hub_id, "to": hub_bus, "weight": 20, "mode": "Walk & Wait", "bidirectional": False
        })

    # Resort busses.
    for bus_source in bus_sources:
        bus_source_id = clean_id(bus_source)
        bus_source_stop_id = f"{bus_source_id}_BUS"

        # Create the bus stop node for the resort and connect with walk (and wait if boarding).
        bus_connections.append({
            "from": bus_source_id, "to": bus_source_stop_id, "weight": 20, "mode": "Walk & Wait", "bidirectional": False
        })
        bus_connections.append({
            "from": bus_source_stop_id, "to": bus_source_id, "weight": 5, "mode": "Walk", "bidirectional": False
        })

        for bus_destination, weight in bus_destinations.items():
            if not weight:
                continue
            bus_destination_id = clean_id(bus_destination)
            if not has_premium_transit(bus_source_id,
                                       bus_destination_id,
                                       final_data["connections"],
                                       no_bus_nodes=no_bus_nodes,
                                       display_names=final_data["display_names"]):

                # Handle bus stops at resorts. Connect with walk (and wait if boarding).
                bus_destination_stop_id = f"{bus_destination_id}_BUS"

                bus_connections.append({
                    "from": bus_source_stop_id, "to": bus_destination_stop_id, "weight": weight, "mode": "Bus", "bidirectional": True
                })

    # Non-Disney resort busses. 
    for bus_route in manual_busses:
        bus_source, bus_destination, travel_weight, wait_weight, bidirectional = bus_route
        bus_source_id = clean_id(bus_source)
        bus_destination_id = clean_id(bus_destination)

        if not has_premium_transit(bus_source_id,
                                   bus_destination_id,
                                   final_data["connections"],
                                   no_bus_nodes=no_bus_nodes,
                                   display_names=final_data["display_names"]):

            bus_source_stop_id = f"{bus_source_id}_BUS"
            bus_destination_stop_id = f"{bus_destination_id}_BUS"
            
            # Create and connect the bus stop.
            if bus_source_stop_id not in final_data["display_names"].values():
                final_data["display_names"][f"{bus_source} - Bus Stop"] = bus_source_stop_id
                bus_connections.append({
                    "from": bus_source_id, "to": bus_source_stop_id, "weight": wait_weight, "mode": "Walk & Wait", "bidirectional": False
                })
                bus_connections.append({
                    "from": bus_source_stop_id, "to": bus_source_id, "weight": 1, "mode": "Walk", "bidirectional": False
                })

            # Connect source and destination with a bus edge.
            bus_connections.append({
                "from": bus_source_stop_id, "to": bus_destination_stop_id, "weight": travel_weight, "mode": "Bus", "bidirectional": bidirectional
            })

    # Internal resort bus loops.
    for bus_route in internal_bus_loops:
        resort = bus_route["resort"]
        stops = bus_route["stops"]
        resort_id = clean_id(resort)
        prior_stop = None
        for stop in stops:
            stop_id = clean_id(stop)
            resort_stop_id = f"{resort_id}_{stop_id}"
            resort_bus_stop_id = f"{resort_id}_{stop_id}_BUS"

            # Conditionally create the bus display name.
            if resort_bus_stop_id not in final_data["display_names"].values():
                final_data["display_names"][f"{resort} ({stop})"] = resort_stop_id
                final_data["display_names"][f"{resort} ({stop}) Inbound Bus Stop"] = resort_bus_stop_id + "_INBOUND"
                final_data["display_names"][f"{resort} ({stop}) Outbound Bus Stop"] = resort_bus_stop_id + "_OUTBOUND"

            # Connect the resort stop to the bus.
            bus_connections.append({
                "from": resort_stop_id, "to": resort_bus_stop_id + "_OUTBOUND", "weight": 20, "mode": "Walk & Wait", "bidirectional": False}
            )
            bus_connections.append({
                "from": resort_bus_stop_id + "_INBOUND", "to": resort_stop_id, "weight": 5, "mode": "Walk", "bidirectional": False}
            )
            if prior_stop:
                bus_connections.append(
                    {"from": prior_stop + "_OUTBOUND", "to": resort_bus_stop_id + "_OUTBOUND", "weight": 3, "mode": "Bus", "bidirectional": False}
                )
                bus_connections.append(
                    {"from": prior_stop + "_INBOUND", "to": resort_bus_stop_id + "_INBOUND", "weight": 3, "mode": "Bus", "bidirectional": False}
                )
            else:
                # Connect from a central hub if this is the first stop in the loop.
                for hub, weight in bus_destinations.items():
                    hub_id = clean_id(hub)
                    bus_connections.append({
                        "from": hub_id + "_BUS", "to": resort_bus_stop_id + "_INBOUND", "weight": weight, "mode": "Bus", "bidirectional": False
                    })
            prior_stop = resort_bus_stop_id
        # Connect to a central hub at the end of the loop.
        for hub, weight in bus_destinations.items():
            hub_id = clean_id(hub)
            if prior_stop:
                bus_connections.append({
                    "from": prior_stop + "_OUTBOUND", "to": hub_id + "_BUS", "weight": weight, "mode": "Bus", "bidirectional": False
                })

    # Park hopper busses.
    parks = ["MK_MAIN", "EP_MAIN", "HS_MAIN", "AK_MAIN"]
    for i, park_a in enumerate(parks):
        for park_b in parks[i+1:]:
            # Parks are always connected to each other by bus (or other modes handled elsewhere)
            if not has_premium_transit(park_a, park_b, final_data["connections"], no_bus_nodes=no_bus_nodes, display_names=final_data["display_names"]):
                bus_connections.append({
                    "from": park_a + "_BUS",
                    "to": park_b + "_BUS", 
                    "weight": 15, "mode": "Bus", "bidirectional": True
                })

    return bus_connections

def convert_to_json(all_raw_data, manual_busses, bus_only=[], internal_bus_loops=[]):
    """ Convert existing data and generate busses into one dictionary. """
    connections = []
    display_names = {}

    for data_list in all_raw_data:
        for u_raw, v_raw, weight, mode, bidirectional in data_list:
            u_id = clean_id(u_raw)
            v_id = clean_id(v_raw)

            # Keep human-readable labels for all raw nodes (including boat sub-stops)
            display_names[u_raw] = u_id
            display_names[v_raw] = v_id

            connections.append({
                "from": u_id,
                "to": v_id,
                "weight": weight,
                "mode": mode,
                "bidirectional": bidirectional
            })
    
    for bus_only_u in bus_only:
        bus_id = clean_id(bus_only_u)
        display_names[bus_only_u] = bus_id
    all_transport = {"display_names": display_names, "connections": connections}
    all_transport["connections"].extend(generate_busses(all_transport, manual_busses, internal_bus_loops))

    seen = set()
    all_transport["connections"] = [
        c for c in all_transport["connections"]
        if not (
            (k := (c["from"], c["to"], c["weight"], c["mode"], c.get("bidirectional", False))) in seen
            or seen.add(k)
        )
    ]
    insert_bus_display_names(all_transport)
    return all_transport

if __name__ == "__main__":
    # Run the script
    final_data = convert_to_json([monorails, boats, skyliners, walks], manual_busses, bus_only, internal_bus_loops)

    # Output to file
    with open('data/wdw_graph.json', 'w') as f:
        json.dump(final_data, f, indent=2)

    print(f"Successfully converted {len(final_data['connections'])} connections.")
