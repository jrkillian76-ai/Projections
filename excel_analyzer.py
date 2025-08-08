#!/usr/bin/env python3
"""
Excel Input Analyzer for Platform Projections Model
Analyzes the Projection_Inputs_v1.0.xlsx file to understand structure and prepare for DAX implementation
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

def analyze_excel_structure(file_path):
    """Analyze the Excel file structure and extract key information"""
    print("🔍 Analyzing Excel Input Structure...")
    print("=" * 50)
    
    # Read all sheets
    excel_file = pd.ExcelFile(file_path)
    print(f"📊 Found {len(excel_file.sheet_names)} sheets: {excel_file.sheet_names}")
    
    analysis = {
        'sheets': {},
        'input_types': set(),
        'months': set(),
        'metrics': {},
        'summary': {}
    }
    
    for sheet_name in excel_file.sheet_names:
        print(f"\n📋 Analyzing Sheet: {sheet_name}")
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        
        # Store sheet analysis
        sheet_analysis = {
            'shape': df.shape,
            'columns': list(df.columns),
            'sample_data': df.head(10).to_dict('records') if not df.empty else []
        }
        
        # Analyze main data structure (assuming InputType, Month, Value format)
        if 'InputType' in df.columns and 'Month' in df.columns and 'Value' in df.columns:
            input_types = df['InputType'].unique()
            months = df['Month'].unique()
            
            print(f"   Input Types: {input_types}")
            print(f"   Months: {sorted(months)}")
            
            analysis['input_types'].update(input_types)
            analysis['months'].update(months)
            
            # Analyze value ranges for each input type
            for input_type in input_types:
                type_data = df[df['InputType'] == input_type]
                analysis['metrics'][input_type] = {
                    'count': len(type_data),
                    'months': sorted(type_data['Month'].unique()),
                    'value_range': [type_data['Value'].min(), type_data['Value'].max()],
                    'sample_values': type_data[['Month', 'Value']].to_dict('records')[:5]
                }
        
        analysis['sheets'][sheet_name] = sheet_analysis
    
    # Convert sets to lists for JSON serialization
    analysis['input_types'] = sorted(list(analysis['input_types']))
    analysis['months'] = sorted(list(analysis['months']))
    
    return analysis

def create_calculation_framework(analysis):
    """Create a framework for the calculations based on the Excel analysis"""
    print("\n🏗️ Creating Calculation Framework...")
    print("=" * 50)
    
    framework = {
        'base_inputs': {},
        'interpolation_logic': {},
        'calculation_formulas': {},
        'scenario_modifiers': {}
    }
    
    # Process each input type
    for input_type in analysis['input_types']:
        if input_type in analysis['metrics']:
            metric_data = analysis['metrics'][input_type]
            
            print(f"📈 Processing: {input_type}")
            print(f"   Months: {metric_data['months']}")
            print(f"   Value Range: {metric_data['value_range']}")
            
            # Determine interpolation strategy based on data pattern
            framework['base_inputs'][input_type] = {
                'key_months': metric_data['months'],
                'interpolation_method': 'linear',  # Can be adjusted based on business logic
                'base_values': {str(month): None for month in metric_data['months']}
            }
    
    # Define scenario modifiers
    framework['scenario_modifiers'] = {
        'Base': {'multiplier': 1.0, 'description': 'Base case scenario'},
        'High_10': {'multiplier': 1.1, 'description': '+10% scenario'},
        'Low_10': {'multiplier': 0.9, 'description': '-10% scenario'},
        'High_25': {'multiplier': 1.25, 'description': '+25% scenario'},
        'Low_25': {'multiplier': 0.75, 'description': '-25% scenario'},
        'Custom': {'multiplier': 'variable', 'description': 'Custom adjustable scenario'}
    }
    
    return framework

def generate_dax_templates(framework):
    """Generate DAX code templates for Power BI implementation"""
    print("\n🔧 Generating DAX Templates...")
    print("=" * 50)
    
    dax_code = {
        'measures': [],
        'calculated_columns': [],
        'tables': []
    }
    
    # Generate interpolation measure template
    interpolation_dax = """
// Interpolation Measure Template
InterpolatedValue = 
VAR SelectedMonth = SELECTEDVALUE(DateTable[Month])
VAR SelectedInputType = SELECTEDVALUE(Parameters[InputType])
VAR SelectedScenario = SELECTEDVALUE(Scenarios[ScenarioName])

VAR BaseValue = 
    SWITCH(
        TRUE(),
        SelectedMonth = 1, LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 1),
        SelectedMonth <= 6, 
            VAR M1Value = LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 1)
            VAR M6Value = LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 6)
            RETURN M1Value + (M6Value - M1Value) * (SelectedMonth - 1) / 5,
        SelectedMonth <= 12,
            VAR M6Value = LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 6)
            VAR M12Value = LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 12)
            RETURN M6Value + (M12Value - M6Value) * (SelectedMonth - 6) / 6,
        SelectedMonth <= 24,
            VAR M12Value = LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 12)
            VAR M24Value = LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 24)
            RETURN M12Value + (M24Value - M12Value) * (SelectedMonth - 12) / 12,
        SelectedMonth <= 36,
            VAR M24Value = LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 24)
            VAR M36Value = LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 36)
            RETURN M24Value + (M36Value - M24Value) * (SelectedMonth - 24) / 12,
        // Beyond 36 months, use M36 value with optional growth
        LOOKUPVALUE(Parameters[Value], Parameters[InputType], SelectedInputType, Parameters[Month], 36)
    )

VAR ScenarioMultiplier = 
    SWITCH(
        SelectedScenario,
        "Base", 1.0,
        "High_10", 1.1,
        "Low_10", 0.9,
        "High_25", 1.25,
        "Low_25", 0.75,
        "Custom", SELECTEDVALUE(ScenarioParameters[CustomMultiplier]),
        1.0
    )

RETURN BaseValue * ScenarioMultiplier
"""
    
    dax_code['measures'].append(interpolation_dax)
    
    # Generate account calculation measure
    account_calc_dax = """
// Account Calculation Measure
TotalAccounts = 
VAR CurrentMonth = SELECTEDVALUE(DateTable[Month])
VAR SelectedScenario = SELECTEDVALUE(Scenarios[ScenarioName])

VAR BaseAccounts = 
    SWITCH(
        TRUE(),
        CurrentMonth <= 1, [InterpolatedValue for Accounts at Month 1],
        CurrentMonth <= 6, [InterpolatedValue for Accounts at Month 6], 
        CurrentMonth <= 12, [InterpolatedValue for Accounts at Month 12],
        CurrentMonth <= 24, [InterpolatedValue for Accounts at Month 24],
        [InterpolatedValue for Accounts at Month 36]
    )

RETURN BaseAccounts
"""
    
    dax_code['measures'].append(account_calc_dax)
    
    # Generate transaction volume calculations
    transaction_dax = """
// Transaction Volume Calculations
TransactionVolume = 
VAR Accounts = [TotalAccounts]
VAR TransactionRate = [InterpolatedValue] // Assuming this gets the appropriate rate
VAR UsageRate = [InterpolatedValue] // Assuming this gets the usage rate

RETURN Accounts * TransactionRate * UsageRate
"""
    
    dax_code['measures'].append(transaction_dax)
    
    return dax_code

def save_analysis_results(analysis, framework, dax_code, output_dir="analysis_output"):
    """Save all analysis results to files"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save analysis
    with open(output_path / "excel_analysis.json", 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    # Save framework
    with open(output_path / "calculation_framework.json", 'w') as f:
        json.dump(framework, f, indent=2, default=str)
    
    # Save DAX code
    with open(output_path / "dax_templates.txt", 'w') as f:
        f.write("// DAX Templates for Platform Projections Model\n")
        f.write("// Generated from Excel Analysis\n\n")
        
        f.write("// MEASURES\n")
        f.write("=" * 50 + "\n\n")
        for measure in dax_code['measures']:
            f.write(measure + "\n\n")
    
    print(f"📁 Analysis results saved to: {output_path}")
    return output_path

def main():
    """Main analysis function"""
    excel_file = "Projection_Inputs_v1.0.xlsx"
    
    if not Path(excel_file).exists():
        print(f"❌ Excel file not found: {excel_file}")
        return
    
    # Analyze Excel structure
    analysis = analyze_excel_structure(excel_file)
    
    # Create calculation framework
    framework = create_calculation_framework(analysis)
    
    # Generate DAX templates
    dax_code = generate_dax_templates(framework)
    
    # Save results
    output_path = save_analysis_results(analysis, framework, dax_code)
    
    print("\n✅ Analysis Complete!")
    print(f"📊 Found {len(analysis['input_types'])} input types")
    print(f"📅 Covering {len(analysis['months'])} key months: {analysis['months']}")
    print(f"🎯 Generated DAX templates for Power BI implementation")
    
    return analysis, framework, dax_code

if __name__ == "__main__":
    analysis, framework, dax_code = main()