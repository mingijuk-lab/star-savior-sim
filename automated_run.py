
import sys
import os
import json
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

import Core.calc_dps as calc_dps

def automated_main():
    # Mock interactive substats with 0.0 for standard baseline test
    calc_dps.get_interactive_substats = lambda: {
        "$ATK$": 0.0,
        "$SPD$": 0.0,
        "$CR$": 0.0,
        "$CD$": 0.0,
        "METRIC": 1
    }
    
    # Run original main
    calc_dps.main()

if __name__ == "__main__":
    automated_main()
