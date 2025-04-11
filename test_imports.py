# test_imports.py
try:
    from src.models.base_models import PositionSide, Signal
    print("✓ Successfully imported from models")
    
    from src.risk.risk_manager import RiskManager
    print("✓ Successfully imported RiskManager")
    
    from src.utils.monitoring import MonitoringSystem
    print("✓ Successfully imported MonitoringSystem")
    
    # Create instances to test initialization
    risk_config = {'max_drawdown': 0.5}
    risk_manager = RiskManager(risk_config)
    print("✓ Successfully created RiskManager instance")
    
    monitoring_config = {'alerts': {}}
    monitoring_system = MonitoringSystem(monitoring_config, risk_manager)
    print("✓ Successfully created MonitoringSystem instance")
    
    print("All imports and initializations successful!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()