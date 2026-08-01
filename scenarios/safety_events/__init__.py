"""Registry of the 23 safety-critical scenario classes."""
from scenarios.safety_events.pedestrian_crossing import PedestrianCrossing
from scenarios.safety_events.cut_in import CutIn
from scenarios.safety_events.red_light_violation import RedLightViolation
from scenarios.safety_events.unprotected_left import UnprotectedLeft
from scenarios.safety_events.emergency_vehicle import EmergencyVehicle
from scenarios.safety_events.cyclist_merge import CyclistMerge
from scenarios.safety_events.wrong_way_driver import WrongWayDriver
from scenarios.safety_events.occluded_pedestrian import OccludedPedestrian
from scenarios.safety_events.construction_zone import ConstructionZone
from scenarios.safety_events.adverse_weather import AdverseWeather
from scenarios.safety_events.night_pedestrian import NightPedestrian
from scenarios.safety_events.jaywalking_group import JaywalkingGroup
from scenarios.safety_events.sudden_brake import SuddenBrake
from scenarios.safety_events.stationary_hazard import StationaryHazard
from scenarios.safety_events.intersection_gridlock import IntersectionGridlock
from scenarios.safety_events.motorcycle_lane_splitting import MotorcycleLaneSplitting
from scenarios.safety_events.bus_stop_pedestrian import BusStopPedestrian
from scenarios.safety_events.highway_onramp_merge import HighwayOnrampMerge
from scenarios.safety_events.dui_erratic_weave import DuiErraticWeave
from scenarios.safety_events.running_stop_sign import RunningStopSign
from scenarios.safety_events.truck_breakdown import TruckBreakdown
from scenarios.safety_events.cyclist_overtake_close import CyclistOvertakeClose
from scenarios.safety_events.road_debris import RoadDebris

REGISTRY = {
    "pedestrian_crossing": PedestrianCrossing,
    "cut_in": CutIn,
    "red_light_violation": RedLightViolation,
    "unprotected_left": UnprotectedLeft,
    "emergency_vehicle": EmergencyVehicle,
    "cyclist_merge": CyclistMerge,
    "wrong_way_driver": WrongWayDriver,
    "occluded_pedestrian": OccludedPedestrian,
    "construction_zone": ConstructionZone,
    "adverse_weather": AdverseWeather,
    "night_pedestrian": NightPedestrian,
    "jaywalking_group": JaywalkingGroup,
    "sudden_brake": SuddenBrake,
    "stationary_hazard": StationaryHazard,
    "intersection_gridlock": IntersectionGridlock,
    "motorcycle_lane_splitting": MotorcycleLaneSplitting,
    "bus_stop_pedestrian": BusStopPedestrian,
    "highway_onramp_merge": HighwayOnrampMerge,
    "dui_erratic_weave": DuiErraticWeave,
    "running_stop_sign": RunningStopSign,
    "truck_breakdown": TruckBreakdown,
    "cyclist_overtake_close": CyclistOvertakeClose,
    "road_debris": RoadDebris,
}
