# Scenario Catalog

SantaClara Aegis ships **23 safety-critical scenario classes**, each mapped to
a recognized regulatory or pre-crash typology. Every scenario is constructed
from **relative road topology** (lanes, junctions, signals), so it transfers
from CARLA's stock map to a client's real corridor.

Categories: **VRU** (vulnerable road users) · **Intersection** · **Highway** ·
**Weather** · **Incident**.

| # | Key | Scenario | Category | Trigger dist (m) | Regulatory reference |
|---|-----|----------|----------|------------------|----------------------|
| 1 | `pedestrian_crossing` | Sudden Pedestrian Crossing | VRU | 24.0 | CA DMV AV Program – VRU Interaction |
| 2 | `cut_in` | Aggressive Vehicle Cut-In | Highway | 16.0 | NHTSA Pre-Crash: Lane Change / Cut-In |
| 3 | `red_light_violation` | Cross-Traffic Red Light Runner | Intersection | 45.0 | CA CVC 21453 |
| 4 | `unprotected_left` | Oncoming Unprotected Left Turn | Intersection | 42.0 | NHTSA Pre-Crash: LTAP/OD |
| 5 | `emergency_vehicle` | Emergency Vehicle Yield | Incident | 20.0 | CA CVC 21806 |
| 6 | `cyclist_merge` | Cyclist Merging Into Lane | VRU | 18.0 | CA CVC 21760 (Three Feet for Safety) |
| 7 | `wrong_way_driver` | Head-On Wrong-Way Driver | Incident | 55.0 | NHTSA Pre-Crash: Opposite Direction |
| 8 | `occluded_pedestrian` | Occluded Pedestrian Dash-Out | VRU | 15.0 | Euro NCAP CPNC-style |
| 9 | `construction_zone` | Construction Zone Forced Merge | Incident | 38.0 | CA MUTCD Temporary Traffic Control |
| 10 | `adverse_weather` | Hard Rain + Lead Vehicle Brake | Weather | 17.0 | CA DMV AV Program – Adverse Weather |
| 11 | `night_pedestrian` | Night-Time Pedestrian Crossing | VRU | 22.0 | FMVSS 127-aligned Low-Light PAEB |
| 12 | `jaywalking_group` | Multi-Pedestrian Jaywalking Group | VRU | 26.0 | CA DMV AV Program – VRU Interaction |
| 13 | `sudden_brake` | Lead Vehicle Panic Brake | Highway | 15.0 | NHTSA Pre-Crash: Rear-End (Lead Decel.) |
| 14 | `stationary_hazard` | Stalled Vehicle In Lane | Incident | 32.0 | NHTSA Pre-Crash: Rear-End (Lead Stopped) |
| 15 | `intersection_gridlock` | Signal Failure + Cross Traffic | Intersection | 40.0 | CA CVC 21800(d) |
| 16 | `motorcycle_lane_splitting` | Motorcycle Lane-Splitting | Highway | 14.0 | CA V.C. 21658.1 |
| 17 | `bus_stop_pedestrian` | Bus-Stop Pedestrian Dart-Out | VRU | 22.0 | CA DMV AV Program – Transit VRUs |
| 18 | `highway_onramp_merge` | Freeway On-Ramp Merge Conflict | Highway | 30.0 | NHTSA Pre-Crash: Lane Change / Merge |
| 19 | `dui_erratic_weave` | Impaired Driver Erratic Weave | Incident | 18.0 | NHTSA Impairment Precursor |
| 20 | `running_stop_sign` | Running Stop Sign / Cross Traffic | Intersection | 22.0 | CA CVC 22450 |
| 21 | `truck_breakdown` | Disabled Truck Blocking Lane | Incident | 32.0 | Caltrans Move-Over / FMS |
| 22 | `cyclist_overtake_close` | Unsafe Close-Pass of Cyclist | VRU | 24.0 | CA V.C. 21760 |
| 23 | `road_debris` | Roadway Debris / Object Avoidance | Incident | 30.0 | Caltrans FMS – Object on Roadway |

## Adding a scenario

New scenarios follow the contract in `scenarios/base_scenario.py`:

```python
class MyScenario:
    def setup(self, ctx):     ...   # spawn threat actors relative to ego topology
    def on_tick(self, ctx, frame, t): ...   # trigger / drive the event
    def cleanup(self, ctx):   ...   # (handled by base; destroy registered actors)
```

Register it in `config/scenarios.json` with a `title`, `weather`, `trigger_dist`,
`needs` (e.g. `adjacent_lane`, `junction`), and the relevant `dmv_ref`. The
behavior model and scoring live in the proprietary `elite/` engine.
