"""
Bitcoin Options Analytics Platform - Working Streamlit Dashboard

This dashboard provides a web-based interface for the Taylor expansion PnL analysis.
Connects to the fully implemented backend modules for real functionality.

Usage:
    streamlit run dashboard/app.py
"""

import sys
import logging
import traceback
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_backend_availability():
    """Test if backend modules are available and working."""
    try:
        from src.analytics.pnl_simulator import TaylorExpansionPnL, ScenarioParameters
        from src.models.black_scholes import BlackScholesModel, OptionParameters, OptionType
        from src.data.collectors import DeribitCollector
        from src import __version__
        return True, None
    except Exception as e:
        return False, str(e)

def create_working_dashboard():
    """Create the main working dashboard."""
    
    # Test backend availability
    backend_available, error_msg = test_backend_availability()
    
    if not backend_available:
        st.error("❌ **Backend modules not available**")
        st.error(f"Error: {error_msg}")
        st.info("💡 **Solutions:**")
        st.info("1. Make sure you're in the project root directory")
        st.info("2. Install dependencies: `pip install -r requirements.txt`")
        st.info("3. Check that src/ directory contains all modules")
        return
    
    # Import backend modules
    from src.analytics.pnl_simulator import TaylorExpansionPnL, ScenarioParameters
    from src.models.black_scholes import BlackScholesModel, OptionParameters, OptionType
    from src.data.collectors import DeribitCollector
    from src import __version__
    
    # Page configuration
    st.set_page_config(
        page_title="Bitcoin Options Analytics",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Header
    st.title("🚀 Bitcoin Options Analytics Platform")
    st.markdown(f"**Version:** {__version__} | **Status:** ✅ Working Implementation")
    
    # Sidebar for navigation
    st.sidebar.title("📋 Navigation")
    page = st.sidebar.selectbox(
        "Choose Analysis Type:",
        ["🎯 Taylor Expansion PnL", "📊 Data Collection", "🧮 Greeks Calculator", "📈 Scenario Analysis", "ℹ️ System Status"]
    )
    
    if page == "🎯 Taylor Expansion PnL":
        create_pnl_analysis_page()
    elif page == "📊 Data Collection":
        create_data_collection_page()
    elif page == "🧮 Greeks Calculator":
        create_greeks_calculator_page()
    elif page == "📈 Scenario Analysis":
        create_scenario_analysis_page()
    elif page == "ℹ️ System Status":
        create_system_status_page()

def create_pnl_analysis_page():
    """Create the main Taylor expansion PnL analysis page."""
    from src.analytics.pnl_simulator import TaylorExpansionPnL
    from src.models.black_scholes import OptionParameters, OptionType
    
    st.header("🎯 Taylor Expansion PnL Analysis")
    st.markdown("**Primary Feature:** `ΔC ≈ δΔS + ½γ(ΔS)² + θΔt + νΔσ`")
    
    # Create columns for input parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📊 Option Parameters")
        spot_price = st.number_input(
            "Current BTC Price ($)",
            min_value=1000.0,
            max_value=200000.0,
            value=30000.0,
            step=1000.0,
            help="Current Bitcoin spot price"
        )
        
        strike_price = st.number_input(
            "Strike Price ($)",
            min_value=1000.0,
            max_value=200000.0,
            value=32000.0,
            step=1000.0,
            help="Option strike price"
        )
        
        time_to_expiry = st.number_input(
            "Time to Expiry (days)",
            min_value=1.0,
            max_value=365.0,
            value=30.0,
            step=1.0,
            help="Days until option expiration"
        )
    
    with col2:
        st.subheader("📈 Market Parameters")
        volatility = st.slider(
            "Implied Volatility (%)",
            min_value=10.0,
            max_value=200.0,
            value=80.0,
            step=5.0,
            help="Implied volatility percentage"
        ) / 100.0
        
        risk_free_rate = st.slider(
            "Risk-Free Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=5.0,
            step=0.1,
            help="Annual risk-free interest rate"
        ) / 100.0
        
        option_type = st.selectbox(
            "Option Type",
            ["Call", "Put"],
            help="Type of option"
        )
    
    with col3:
        st.subheader("⚡ Scenario Shocks")
        spot_shock = st.slider(
            "Spot Price Shock (%)",
            min_value=-50.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
            help="Percentage change in spot price"
        ) / 100.0
        
        vol_shock = st.slider(
            "Volatility Shock (%)",
            min_value=-50.0,
            max_value=100.0,
            value=20.0,
            step=5.0,
            help="Percentage change in volatility"
        ) / 100.0
        
        time_decay = st.number_input(
            "Time Decay (days)",
            min_value=0.0,
            max_value=30.0,
            value=1.0,
            step=0.5,
            help="Days of time decay"
        )
    
    # Calculate PnL button
    if st.button("🚀 **Calculate Taylor Expansion PnL**", type="primary"):
        try:
            with st.spinner("Calculating PnL components..."):
                # Create option parameters
                params = OptionParameters(
                    spot_price=spot_price,
                    strike_price=strike_price,
                    time_to_expiry=time_to_expiry / 365.25,  # Convert to years
                    volatility=volatility,
                    risk_free_rate=risk_free_rate,
                    option_type=OptionType.CALL if option_type == "Call" else OptionType.PUT
                )
                
                # Initialize PnL simulator
                pnl_sim = TaylorExpansionPnL()
                
                # Calculate PnL components
                pnl_components = pnl_sim.calculate_pnl_components(
                    params,
                    spot_shock=spot_shock,
                    vol_shock=vol_shock,
                    time_decay_days=time_decay
                )
                
                # Display results
                st.success("✅ **PnL Analysis Complete!**")
                
                # Create results columns
                res_col1, res_col2 = st.columns(2)
                
                with res_col1:
                    st.subheader("📊 PnL Breakdown")
                    
                    # PnL components table
                    pnl_data = {
                        "Component": ["δΔS (Delta)", "½γ(ΔS)² (Gamma)", "θΔt (Theta)", "νΔσ (Vega)", "**Total PnL**"],
                        "Value ($)": [
                            f"${pnl_components.delta_pnl:.2f}",
                            f"${pnl_components.gamma_pnl:.2f}",
                            f"${pnl_components.theta_pnl:.2f}",
                            f"${pnl_components.vega_pnl:.2f}",
                            f"**${pnl_components.total_pnl:.2f}**"
                        ],
                        "Contribution (%)": [
                            f"{(pnl_components.delta_pnl/pnl_components.total_pnl*100) if pnl_components.total_pnl != 0 else 0:.1f}%",
                            f"{(pnl_components.gamma_pnl/pnl_components.total_pnl*100) if pnl_components.total_pnl != 0 else 0:.1f}%",
                            f"{(pnl_components.theta_pnl/pnl_components.total_pnl*100) if pnl_components.total_pnl != 0 else 0:.1f}%",
                            f"{(pnl_components.vega_pnl/pnl_components.total_pnl*100) if pnl_components.total_pnl != 0 else 0:.1f}%",
                            "100.0%"
                        ]
                    }
                    
                    st.dataframe(pd.DataFrame(pnl_data), hide_index=True)
                    
                    # Key metrics
                    st.metric("Original Option Price", f"${pnl_components.original_price:.2f}")
                    st.metric("New Theoretical Price", f"${pnl_components.new_theoretical_price:.2f}")
                    st.metric("PnL Change", f"${pnl_components.total_pnl:.2f}", 
                             f"{(pnl_components.total_pnl/pnl_components.original_price*100) if pnl_components.original_price > 0 else 0:.2f}%")
                
                with res_col2:
                    st.subheader("📈 Visual Breakdown")
                    
                    # PnL components chart
                    components = ["Delta", "Gamma", "Theta", "Vega"]
                    values = [
                        pnl_components.delta_pnl,
                        pnl_components.gamma_pnl,
                        pnl_components.theta_pnl,
                        pnl_components.vega_pnl
                    ]
                    colors = ["blue", "green", "red", "orange"]
                    
                    fig = go.Figure(data=[
                        go.Bar(
                            x=components,
                            y=values,
                            marker_color=colors,
                            text=[f"${v:.2f}" for v in values],
                            textposition='auto'
                        )
                    ])
                    
                    fig.update_layout(
                        title="PnL Components Breakdown",
                        xaxis_title="Greeks Components",
                        yaxis_title="PnL ($)",
                        showlegend=False,
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Formula display
                st.subheader("📐 Taylor Expansion Formula")
                st.latex(r"\Delta C \approx \delta \Delta S + \frac{1}{2}\gamma (\Delta S)^2 + \theta \Delta t + \nu \Delta \sigma")
                
                # Interpretation
                st.subheader("💡 Interpretation")
                interpretation = []
                if pnl_components.delta_pnl > 0:
                    interpretation.append(f"✅ **Delta gain:** ${pnl_components.delta_pnl:.2f} from favorable spot price movement")
                else:
                    interpretation.append(f"❌ **Delta loss:** ${pnl_components.delta_pnl:.2f} from unfavorable spot price movement")
                
                if pnl_components.gamma_pnl > 0:
                    interpretation.append(f"✅ **Gamma gain:** ${pnl_components.gamma_pnl:.2f} from convexity benefit")
                else:
                    interpretation.append(f"❌ **Gamma loss:** ${pnl_components.gamma_pnl:.2f} from convexity drag")
                
                if pnl_components.theta_pnl < 0:
                    interpretation.append(f"⏰ **Time decay:** ${pnl_components.theta_pnl:.2f} from {time_decay} day(s) passing")
                
                if pnl_components.vega_pnl > 0:
                    interpretation.append(f"📈 **Volatility gain:** ${pnl_components.vega_pnl:.2f} from volatility increase")
                else:
                    interpretation.append(f"📉 **Volatility loss:** ${pnl_components.vega_pnl:.2f} from volatility decrease")
                
                for interp in interpretation:
                    st.markdown(interp)
                
        except Exception as e:
            st.error(f"❌ **Calculation failed:** {str(e)}")
            with st.expander("🔍 Error Details"):
                st.code(traceback.format_exc())

def create_data_collection_page():
    """Create data collection testing page."""
    from src.data.collectors import DeribitCollector
    
    st.header("📊 Data Collection")
    st.markdown("Test the data collection system and fetch real options data.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌐 API Connection Test")
        if st.button("Test Deribit API Connection"):
            with st.spinner("Testing connection..."):
                try:
                    collector = DeribitCollector()
                    success = collector.test_connection()
                    
                    if success:
                        st.success("✅ **API Connection Successful!**")
                        st.info("🎯 Ready to collect options data")
                    else:
                        st.error("❌ **API Connection Failed**")
                        st.warning("Check internet connection and API status")
                        
                except Exception as e:
                    st.error(f"❌ **Connection Error:** {str(e)}")
    
    with col2:
        st.subheader("📅 Data Collection")
        
        # Date selection
        end_date = st.date_input(
            "End Date",
            value=date(2024, 12, 31),  # Use historical dates that have data
            help="End date for data collection"
        )
        
        start_date = st.date_input(
            "Start Date", 
            value=end_date - timedelta(days=1),
            help="Start date for data collection"
        )
        
        currency = st.selectbox("Currency", ["BTC", "ETH"], help="Cryptocurrency to analyze")
        
        if st.button("Collect Options Data"):
            if start_date <= end_date:
                with st.spinner(f"Collecting {currency} options data..."):
                    try:
                        from src.data.collectors import collect_options_data
                        
                        data = collect_options_data(
                            currency=currency,
                            start_date=start_date,
                            end_date=end_date
                        )
                        
                        if not data.empty:
                            st.success(f"✅ **Collected {len(data)} option records!**")
                            
                            # Display sample data
                            st.subheader("📋 Sample Data")
                            st.dataframe(data.head(10))
                            
                            # Data summary
                            st.subheader("📊 Data Summary")
                            col_a, col_b, col_c = st.columns(3)
                            
                            with col_a:
                                st.metric("Total Records", len(data))
                                st.metric("Unique Strikes", data['strike_price'].nunique())
                            
                            with col_b:
                                st.metric("Call Options", len(data[data['option_type'] == 'call']))
                                st.metric("Put Options", len(data[data['option_type'] == 'put']))
                            
                            with col_c:
                                st.metric("Avg IV", f"{data['implied_volatility'].mean():.2%}")
                                st.metric("Price Range", f"${data['underlying_price'].min():.0f} - ${data['underlying_price'].max():.0f}")
                        else:
                            st.warning("⚠️ **No data collected**")
                            st.info("Try different dates or check API status")
                            
                    except Exception as e:
                        st.error(f"❌ **Data collection failed:** {str(e)}")
            else:
                st.error("❌ Start date must be before end date")

def create_greeks_calculator_page():
    """Create Greeks calculation page."""
    from src.models.black_scholes import BlackScholesModel, OptionParameters, OptionType
    
    st.header("🧮 Greeks Calculator")
    st.markdown("Calculate Black-Scholes Greeks for individual options.")
    
    # Input parameters
    col1, col2 = st.columns(2)
    
    with col1:
        spot = st.number_input("Spot Price ($)", value=30000.0, min_value=1.0)
        strike = st.number_input("Strike Price ($)", value=32000.0, min_value=1.0)
        time_to_exp = st.number_input("Time to Expiry (days)", value=30.0, min_value=0.1) / 365.25
    
    with col2:
        vol = st.slider("Volatility (%)", 1.0, 200.0, 80.0) / 100.0
        rate = st.slider("Risk-Free Rate (%)", 0.0, 20.0, 5.0) / 100.0
        opt_type = st.selectbox("Option Type", ["Call", "Put"])
    
    if st.button("Calculate Greeks"):
        try:
            bs_model = BlackScholesModel()
            
            params = OptionParameters(
                spot_price=spot,
                strike_price=strike,
                time_to_expiry=time_to_exp,
                volatility=vol,
                risk_free_rate=rate,
                option_type=OptionType.CALL if opt_type == "Call" else OptionType.PUT
            )
            
            greeks = bs_model.calculate_greeks(params)
            
            st.success("✅ **Greeks Calculated!**")
            
            # Display results
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Option Price", f"${greeks.option_price:.2f}")
                st.metric("Delta", f"{greeks.delta:.4f}")
            
            with col_b:
                st.metric("Gamma", f"{greeks.gamma:.6f}")
                st.metric("Theta", f"${greeks.theta:.4f} (daily)")
            
            with col_c:
                st.metric("Vega", f"${greeks.vega:.4f} (per 1% vol)")
                st.metric("Rho", f"${greeks.rho:.4f} (per 1% rate)")
            
            # Greeks interpretation
            st.subheader("💡 Greeks Interpretation")
            st.markdown(f"- **Delta ({greeks.delta:.4f}):** For every $1 move in {opt_type.lower()}, option price changes by ${greeks.delta:.4f}")
            st.markdown(f"- **Gamma ({greeks.gamma:.6f}):** Delta changes by {greeks.gamma:.6f} for every $1 move in underlying")
            st.markdown(f"- **Theta (${greeks.theta:.4f}):** Option loses ${abs(greeks.theta):.4f} value per day (time decay)")
            st.markdown(f"- **Vega (${greeks.vega:.4f}):** Option price changes by ${greeks.vega:.4f} for 1% volatility change")
            
        except Exception as e:
            st.error(f"❌ **Calculation failed:** {str(e)}")

def create_scenario_analysis_page():
    """Create comprehensive scenario analysis page."""
    from src.analytics.pnl_simulator import TaylorExpansionPnL, ScenarioParameters
    from src.models.black_scholes import OptionParameters, OptionType
    
    st.header("📈 Scenario Analysis")
    st.markdown("Comprehensive stress testing with multiple scenarios.")
    
    # Parameters
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Base Option")
        spot = st.number_input("Spot Price", value=30000.0, key="scenario_spot")
        strike = st.number_input("Strike Price", value=32000.0, key="scenario_strike")
        tte = st.number_input("Time to Expiry (days)", value=30.0, key="scenario_tte") / 365.25
        vol = st.slider("Volatility (%)", 1.0, 200.0, 80.0, key="scenario_vol") / 100.0
        opt_type = st.selectbox("Option Type", ["Call", "Put"], key="scenario_type")
    
    with col2:
        st.subheader("⚡ Scenario Ranges")
        spot_range = st.slider("Spot Shock Range (%)", 1, 50, 20, key="spot_range")
        vol_range = st.slider("Vol Shock Range (%)", 1, 100, 30, key="vol_range")
        time_max = st.slider("Max Time Decay (days)", 1, 30, 7, key="time_range")
    
    if st.button("🚀 Run Scenario Analysis", key="run_scenarios"):
        try:
            with st.spinner("Running scenario analysis..."):
                # Create parameters
                params = OptionParameters(
                    spot_price=spot,
                    strike_price=strike,
                    time_to_expiry=tte,
                    volatility=vol,
                    risk_free_rate=0.05,
                    option_type=OptionType.CALL if opt_type == "Call" else OptionType.PUT
                )
                
                # Create scenarios
                scenarios = ScenarioParameters(
                    spot_shocks=[-spot_range/100, -spot_range/200, 0, spot_range/200, spot_range/100],
                    vol_shocks=[-vol_range/100, -vol_range/200, 0, vol_range/200, vol_range/100],
                    time_decay_days=[0, time_max/2, time_max]
                )
                
                # Run analysis
                pnl_sim = TaylorExpansionPnL()
                results = pnl_sim.analyze_scenarios(params, scenarios)
                summary_df = pnl_sim.create_scenario_summary(results)
                risk_metrics = pnl_sim.calculate_risk_metrics(results)
                
                st.success(f"✅ **Analysis Complete! Generated {len(results)} scenarios**")
                
                # Risk metrics
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.metric("Mean PnL", f"${risk_metrics['mean_pnl']:.2f}")
                    st.metric("Std Dev", f"${risk_metrics['std_pnl']:.2f}")
                
                with col_b:
                    st.metric("95% VaR", f"${risk_metrics['var_95_pnl']:.2f}")
                    st.metric("99% VaR", f"${risk_metrics['var_99_pnl']:.2f}")
                
                with col_c:
                    st.metric("Max Gain", f"${risk_metrics['max_pnl']:.2f}")
                    st.metric("Max Loss", f"${risk_metrics['min_pnl']:.2f}")
                
                # Scenario results table
                st.subheader("📋 Scenario Results")
                st.dataframe(summary_df[['scenario_id', 'total_pnl', 'delta_pnl', 'gamma_pnl', 'theta_pnl', 'vega_pnl']].head(10))
                
                # PnL distribution chart
                st.subheader("📊 PnL Distribution")
                fig = px.histogram(summary_df, x='total_pnl', nbins=20, title="PnL Distribution Across Scenarios")
                fig.add_vline(x=risk_metrics['var_95_pnl'], line_dash="dash", annotation_text="95% VaR")
                st.plotly_chart(fig, use_container_width=True)
                
        except Exception as e:
            st.error(f"❌ **Analysis failed:** {str(e)}")

def create_system_status_page():
    """Create system status and information page."""
    st.header("ℹ️ System Status")
    
    # Test all backend components
    st.subheader("🔧 Backend Component Status")
    
    components = {
        "Taylor Expansion PnL": "src.analytics.pnl_simulator",
        "Black-Scholes Model": "src.models.black_scholes", 
        "Data Collectors": "src.data.collectors",
        "Time Utilities": "src.utils.time_utils",
        "Asset Configuration": "src.config.assets"
    }
    
    for name, module in components.items():
        try:
            __import__(module)
            st.success(f"✅ **{name}** - Working")
        except Exception as e:
            st.error(f"❌ **{name}** - Error: {str(e)}")
    
    # Show package info
    st.subheader("📦 Package Information")
    try:
        from src import get_package_info
        info = get_package_info()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Version:** {info['version']}")
            st.markdown(f"**Python:** {info['python_version']}")
            st.markdown(f"**Core Dependencies:** {info['core_deps_available']}")
        
        with col2:
            st.markdown(f"**All Systems Ready:** {'✅' if info['all_systems_ready'] else '❌'}")
            st.markdown(f"**Advanced Finance:** {'✅' if info['advanced_finance_ready'] else '❌'}")
            st.markdown(f"**Continuous Collector:** {'✅' if info['continuous_collector_ready'] else '❌'}")
            
    except Exception as e:
        st.error(f"Could not load package info: {e}")
    
    # Feature status
    st.subheader("🎯 Feature Implementation Status")
    
    features = {
        "Primary Feature (Taylor Expansion PnL)": "✅ COMPLETE",
        "Black-Scholes Greeks": "✅ COMPLETE", 
        "Data Collection System": "✅ COMPLETE",
        "Asset Discovery": "✅ COMPLETE",
        "Dashboard Interface": "✅ WORKING (This page!)",
        "CLI Interface": "🔄 IN PROGRESS",
        "Continuous Data Collection": "✅ AVAILABLE",
        "Risk Management Tools": "✅ BASIC COMPLETE"
    }
    
    for feature, status in features.items():
        if "✅" in status:
            st.success(f"**{feature}:** {status}")
        elif "🔄" in status:
            st.warning(f"**{feature}:** {status}")
        else:
            st.info(f"**{feature}:** {status}")

def main():
    """Main dashboard entry point."""
    if not STREAMLIT_AVAILABLE:
        print("❌ Streamlit not available!")
        print("Install with: pip install streamlit")
        return
    
    try:
        create_working_dashboard()
        logger.info("Dashboard initialized successfully")
    except Exception as e:
        logger.error(f"Dashboard initialization failed: {e}")
        st.error(f"Dashboard Error: {e}")
        st.error("Full traceback:")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
