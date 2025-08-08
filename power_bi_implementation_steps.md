# Power BI Implementation - CalculationsTable

## 🎯 **Step 1: Create CalculationsTable**

### **In Power BI Power Query Editor:**

1. **Home** → **New Source** → **Blank Query**
2. **Rename** query to `CalculationsTable` 
3. **Advanced Editor** → **Paste this M Code:**

```m
let
    // Step 1: Create Month × Scenario cross join
    MonthRange = List.Numbers(1, 60, 1),
    MonthTable = Table.FromList(MonthRange, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Renamed Month Column" = Table.RenameColumns(MonthTable,{{"Column1", "Month"}}),
    
    // Get scenarios
    ScenariosData = Scenarios,
    
    // Cross join months and scenarios
    CrossJoin = Table.AddColumn(#"Renamed Month Column", "Scenario", each ScenariosData),
    #"Expanded Scenarios" = Table.ExpandTableColumn(CrossJoin, "Scenario", {"ScenarioName", "ScenarioDisplay", "DefaultMultiplier"}, {"ScenarioName", "ScenarioDisplay", "DefaultMultiplier"}),
    
    // Helper function to get interpolated value
    GetInterpolatedValue = (inputType as text, month as number) =>
        let
            FilteredInputs = Table.SelectRows(InterpolatedInputs, each [InputType] = inputType and [Month] = month),
            Value = if Table.RowCount(FilteredInputs) > 0 then FilteredInputs{0}[Value] else 0
        in
            Value,
    
    // Helper function to get scenario multiplier
    GetScenarioMultiplier = (scenarioName as text, defaultMultiplier as number) =>
        if scenarioName = "Custom" then
            1.0 // Will be overridden by slicer
        else
            defaultMultiplier,
    
    // Step 2: Account Calculations
    #"Added Accounts" = Table.AddColumn(#"Expanded Scenarios", "Accounts", each
        let
            BaseAccounts = GetInterpolatedValue("Accounts", [Month]),
            ScenarioMultiplier = GetScenarioMultiplier([ScenarioName], [DefaultMultiplier])
        in
            BaseAccounts * ScenarioMultiplier
    ),
    
    #"Added Active Share" = Table.AddColumn(#"Added Accounts", "ActiveShare", each
        GetInterpolatedValue("ActiveShare", [Month])
    ),
    
    #"Added Active Accounts" = Table.AddColumn(#"Added Active Share", "Active_Accounts", each
        [Accounts] * [ActiveShare]
    ),
    
    #"Added Checking Share" = Table.AddColumn(#"Added Active Accounts", "CheckingShare", each
        GetInterpolatedValue("CheckingShare", [Month])
    ),
    
    #"Added Checking Accounts" = Table.AddColumn(#"Added Checking Share", "Checking_Accounts", each
        [Active_Accounts] * [CheckingShare]
    ),
    
    #"Added Saving Share" = Table.AddColumn(#"Added Checking Accounts", "SavingShare", each
        GetInterpolatedValue("SavingShare", [Month])
    ),
    
    #"Added Savings Accounts" = Table.AddColumn(#"Added Saving Share", "Savings_Accounts", each
        [Active_Accounts] * [SavingShare]
    ),
    
    // Step 3: INFLOW CALCULATIONS
    
    // ACH Inflows
    #"Added ACHinPerActive" = Table.AddColumn(#"Added Savings Accounts", "ACHinPerActive", each
        GetInterpolatedValue("ACHinPerActive", [Month])
    ),
    
    #"Added ACHinQuantity" = Table.AddColumn(#"Added ACHinPerActive", "ACHinQuantity", each
        [Active_Accounts] * [ACHinPerActive]
    ),
    
    #"Added ACHinRate" = Table.AddColumn(#"Added ACHinQuantity", "ACHinRate", each
        GetInterpolatedValue("ACHinRate", [Month])
    ),
    
    #"Added ACHinAmount" = Table.AddColumn(#"Added ACHinRate", "ACHinAmount", each
        [ACHinQuantity] * [ACHinRate]
    ),
    
    // RTP Inflows
    #"Added RTPinPerActive" = Table.AddColumn(#"Added ACHinAmount", "RTPinPerActive", each
        GetInterpolatedValue("RTPinPerActive", [Month])
    ),
    
    #"Added RTPinQuantity" = Table.AddColumn(#"Added RTPinPerActive", "RTPinQuantity", each
        [Active_Accounts] * [RTPinPerActive]
    ),
    
    #"Added RTPinRate" = Table.AddColumn(#"Added RTPinQuantity", "RTPinRate", each
        GetInterpolatedValue("RTPinRate", [Month])
    ),
    
    #"Added RTPinAmount" = Table.AddColumn(#"Added RTPinRate", "RTPinAmount", each
        [RTPinQuantity] * [RTPinRate]
    ),
    
    // Wire Inflows
    #"Added WireInPerActive" = Table.AddColumn(#"Added RTPinAmount", "WireInPerActive", each
        GetInterpolatedValue("WireInPerActive", [Month])
    ),
    
    #"Added WireInQuantity" = Table.AddColumn(#"Added WireInPerActive", "WireInQuantity", each
        [Active_Accounts] * [WireInPerActive]
    ),
    
    #"Added WireInRate" = Table.AddColumn(#"Added WireInQuantity", "WireInRate", each
        GetInterpolatedValue("WireInRate", [Month])
    ),
    
    #"Added WireInAmount" = Table.AddColumn(#"Added WireInRate", "WireInAmount", each
        [WireInQuantity] * [WireInRate]
    ),
    
    // Total Inflows
    #"Added Total Inflows" = Table.AddColumn(#"Added WireInAmount", "Total_Inflows", each
        [ACHinAmount] + [RTPinAmount] + [WireInAmount]
    ),
    
    // Step 4: OUTFLOW CALCULATIONS
    
    // ACH Outflows
    #"Added ACHoutPerActive" = Table.AddColumn(#"Added Total Inflows", "ACHoutPerActive", each
        GetInterpolatedValue("ACHoutPerActive", [Month])
    ),
    
    #"Added ACHoutQuantity" = Table.AddColumn(#"Added ACHoutPerActive", "ACHoutQuantity", each
        [Active_Accounts] * [ACHoutPerActive]
    ),
    
    #"Added ACHoutShare" = Table.AddColumn(#"Added ACHoutQuantity", "ACHoutShare", each
        GetInterpolatedValue("ACHoutShare", [Month])
    ),
    
    #"Added ACHoutAmount" = Table.AddColumn(#"Added ACHoutShare", "ACHoutAmount", each
        [Total_Inflows] * [ACHoutShare]
    ),
    
    #"Added ACHoutRate" = Table.AddColumn(#"Added ACHoutAmount", "ACHoutRate", each
        if [ACHoutQuantity] > 0 then [ACHoutAmount] / [ACHoutQuantity] else 0
    ),
    
    // RTP Outflows
    #"Added RTPoutPerActive" = Table.AddColumn(#"Added ACHoutRate", "RTPoutPerActive", each
        GetInterpolatedValue("RTPoutPerActive", [Month])
    ),
    
    #"Added RTPoutQuantity" = Table.AddColumn(#"Added RTPoutPerActive", "RTPoutQuantity", each
        [Active_Accounts] * [RTPoutPerActive]
    ),
    
    #"Added RTPoutShare" = Table.AddColumn(#"Added RTPoutQuantity", "RTPoutShare", each
        GetInterpolatedValue("RTPoutShare", [Month])
    ),
    
    #"Added RTPoutAmount" = Table.AddColumn(#"Added RTPoutShare", "RTPoutAmount", each
        [Total_Inflows] * [RTPoutShare]
    ),
    
    #"Added RTPoutRate" = Table.AddColumn(#"Added RTPoutAmount", "RTPoutRate", each
        if [RTPoutQuantity] > 0 then [RTPoutAmount] / [RTPoutQuantity] else 0
    ),
    
    // Wire Outflows
    #"Added WireOutPerActive" = Table.AddColumn(#"Added RTPoutRate", "WireOutPerActive", each
        GetInterpolatedValue("WireOutPerActive", [Month])
    ),
    
    #"Added WireOutQuantity" = Table.AddColumn(#"Added WireOutPerActive", "WireOutQuantity", each
        [Active_Accounts] * [WireOutPerActive]
    ),
    
    #"Added WireOutShare" = Table.AddColumn(#"Added WireOutQuantity", "WireOutShare", each
        GetInterpolatedValue("WireOutShare", [Month])
    ),
    
    #"Added WireOutAmount" = Table.AddColumn(#"Added WireOutShare", "WireOutAmount", each
        [Total_Inflows] * [WireOutShare]
    ),
    
    #"Added WireOutRate" = Table.AddColumn(#"Added WireOutAmount", "WireOutRate", each
        if [WireOutQuantity] > 0 then [WireOutAmount] / [WireOutQuantity] else 0
    ),
    
    // Debit Card Outflows
    #"Added DebitCardTransactionsPerActive" = Table.AddColumn(#"Added WireOutRate", "DebitCardTransactionsPerActive", each
        GetInterpolatedValue("DebitCardTransactionsPerActive", [Month])
    ),
    
    #"Added DebitCardTransactionsQuantity" = Table.AddColumn(#"Added DebitCardTransactionsPerActive", "DebitCardTransactionsQuantity", each
        [Active_Accounts] * [DebitCardTransactionsPerActive]
    ),
    
    #"Added DebitCardTransactionShare" = Table.AddColumn(#"Added DebitCardTransactionsQuantity", "DebitCardTransactionShare", each
        GetInterpolatedValue("DebitCardTransactionShare", [Month])
    ),
    
    #"Added DebitCardTransactionAmount" = Table.AddColumn(#"Added DebitCardTransactionShare", "DebitCardTransactionAmount", each
        [Total_Inflows] * [DebitCardTransactionShare]
    ),
    
    #"Added DebitCardTransactionRate" = Table.AddColumn(#"Added DebitCardTransactionAmount", "DebitCardTransactionRate", each
        if [DebitCardTransactionsQuantity] > 0 then [DebitCardTransactionAmount] / [DebitCardTransactionsQuantity] else 0
    ),
    
    // Step 5: FINAL CALCULATIONS
    
    // Total Outflows
    #"Added Total Outflows" = Table.AddColumn(#"Added DebitCardTransactionRate", "Total_Outflows", each
        [ACHoutAmount] + [RTPoutAmount] + [WireOutAmount] + [DebitCardTransactionAmount]
    ),
    
    // Net Remaining for Savings
    #"Added Net Remaining For Savings" = Table.AddColumn(#"Added Total Outflows", "Net_Remaining_For_Savings", each
        [Total_Inflows] - [Total_Outflows]
    ),
    
    // Savings Transfer Rate and Amount
    #"Added SavingsTransferRate" = Table.AddColumn(#"Added Net Remaining For Savings", "SavingsTransferRate", each
        GetInterpolatedValue("SavingsTransferRate", [Month])
    ),
    
    #"Added SavingsTransfers" = Table.AddColumn(#"Added SavingsTransferRate", "SavingsTransfers", each
        [Net_Remaining_For_Savings] * [SavingsTransferRate]
    ),
    
    // Monthly Flows
    #"Added Monthly Checking" = Table.AddColumn(#"Added SavingsTransfers", "Monthly_Checking", each
        [Net_Remaining_For_Savings] - [SavingsTransfers]
    ),
    
    #"Added Monthly Savings" = Table.AddColumn(#"Added Monthly Checking", "Monthly_Savings", each
        [SavingsTransfers]
    ),
    
    // Usage Rates
    #"Added CheckingUsageRate" = Table.AddColumn(#"Added Monthly Savings", "CheckingUsageRate", each
        GetInterpolatedValue("CheckingUsageRate", [Month])
    ),
    
    #"Added SavingsUsageRate" = Table.AddColumn(#"Added CheckingUsageRate", "SavingsUsageRate", each
        GetInterpolatedValue("SavingsUsageRate", [Month])
    ),
    
    #"Added CheckingUsage" = Table.AddColumn(#"Added SavingsUsageRate", "CheckingUsage", each
        [Monthly_Checking] * [CheckingUsageRate]
    ),
    
    #"Added SavingsUsage" = Table.AddColumn(#"Added CheckingUsage", "SavingsUsage", each
        [Monthly_Savings] * [SavingsUsageRate]
    ),
    
    // Final data type cleanup
    #"Changed Types" = Table.TransformColumnTypes(#"Added SavingsUsage",{
        {"Month", Int64.Type},
        {"Accounts", type number},
        {"Active_Accounts", type number},
        {"Checking_Accounts", type number},
        {"Savings_Accounts", type number},
        {"Total_Inflows", type number},
        {"Total_Outflows", type number},
        {"Net_Remaining_For_Savings", type number},
        {"Monthly_Checking", type number},
        {"Monthly_Savings", type number},
        {"CheckingUsage", type number},
        {"SavingsUsage", type number}
    })
    
in
    #"Changed Types"
```

## 🎯 **Step 2: Apply & Test**

1. **Click "Done"** in Advanced Editor
2. **Apply Changes** in Power Query
3. **Close & Apply** to return to main Power BI

## 🔍 **Step 3: Verify Results**

**Expected Results:**
- ✅ **360 rows** (60 months × 6 scenarios)
- ✅ **50+ columns** with all your desired outputs
- ✅ **Base scenario** should match your original calculations

**Quick Test:**
1. **Create a table visual** with:
   - **Rows**: `Month`, `ScenarioDisplay`
   - **Values**: `Accounts`, `Total_Inflows`, `Total_Outflows`
2. **Filter to Base scenario** and **Month 1**
3. **Verify** numbers match your expected values

## 🚨 **If Any Errors Occur:**

**Common Issues:**
1. **"Scenarios table not found"** → Make sure `Scenarios` table exists
2. **"InterpolatedInputs not found"** → Make sure this table exists  
3. **Column name errors** → Check exact spelling in your tables

**Let me know what happens and I'll help debug!**