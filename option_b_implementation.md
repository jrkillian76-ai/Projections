# Option B Implementation: Dynamic Scenarios with Sliders

## 🎯 **Plan: InterpolatedInputs Table + Dynamic DAX Scenarios**

This gives you real-time scenario adjustment with sliders while maintaining performance.

---

## 🚀 **Step 1: Replace InterpolatedInputs Table (M Code)**

### **Action: Create New InterpolatedInputs Table**

1. **Delete existing InterpolatedInputs table**
2. **Create new blank query → Rename to "InterpolatedInputs"**
3. **Paste this M Code:**

```m
let
    // Source: Load Parameters from Excel
    Source = Excel.CurrentWorkbook(){[Name="Parameters"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"InputType", type text}, {"Month", Int64.Type}, {"Value", type number}}),
    
    // Create complete month range (1 to 60)
    MonthRange = List.Numbers(1, 60, 1),
    MonthTable = Table.FromList(MonthRange, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Renamed Month Column" = Table.RenameColumns(MonthTable,{{"Column1", "Month"}}),
    
    // Get unique input types
    InputTypes = Table.Distinct(#"Changed Type", {"InputType"}),
    
    // Cross join: Every month × Every input type
    CrossJoin = Table.AddColumn(#"Renamed Month Column", "InputType", each InputTypes),
    #"Expanded InputTypes" = Table.ExpandTableColumn(CrossJoin, "InputType", {"InputType"}, {"InputType"}),
    
    // Add interpolated values (NO SCENARIOS - just base interpolation)
    #"Added Interpolation" = Table.AddColumn(#"Expanded InputTypes", "Value", each 
        let
            CurrentInputType = [InputType],
            CurrentMonth = [Month],
            
            // Get key month values for this input type
            M1Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 1){0}[Value] otherwise 0,
            M6Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 6){0}[Value] otherwise M1Value,
            M12Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 12){0}[Value] otherwise M6Value,
            M24Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 24){0}[Value] otherwise M12Value,
            M36Value = try Table.SelectRows(#"Changed Type", each [InputType] = CurrentInputType and [Month] = 36){0}[Value] otherwise M24Value,
            
            // Growth rate for beyond month 36
            GrowthRate = try Table.SelectRows(#"Changed Type", each [InputType] = "GrowthRateM37Plus" and [Month] = 37){0}[Value] otherwise 0.01,
            
            // Interpolation logic
            InterpolatedValue = 
                if CurrentMonth = 1 then M1Value
                else if CurrentMonth <= 6 then M1Value + (M6Value - M1Value) * (CurrentMonth - 1) / 5
                else if CurrentMonth <= 12 then M6Value + (M12Value - M6Value) * (CurrentMonth - 6) / 6
                else if CurrentMonth <= 24 then M12Value + (M24Value - M12Value) * (CurrentMonth - 12) / 12
                else if CurrentMonth <= 36 then M24Value + (M36Value - M24Value) * (CurrentMonth - 24) / 12
                else M36Value * Number.Power(1 + GrowthRate, CurrentMonth - 36)
        in
            InterpolatedValue
    ),
    
    // Clean up data types
    #"Changed Value Type" = Table.TransformColumnTypes(#"Added Interpolation",{{"Value", type number}}),
    
    // Reorder columns
    #"Reordered Columns" = Table.ReorderColumns(#"Changed Value Type",{"InputType", "Month", "Value"})
in
    #"Reordered Columns"
```

---

## 🎛️ **Step 2: Create Scenario Tables**

### **A. Scenarios Table (M Code)**

Create new blank query → Rename to "Scenarios":

```m
let
    Source = Table.FromRows({
        {"Base", "Base case scenario", 1.0},
        {"High_10", "+10% account growth", 1.1},
        {"Low_10", "-10% account growth", 0.9},
        {"High_25", "+25% account growth", 1.25},
        {"Low_25", "-25% account growth", 0.75},
        {"Custom", "Custom adjustable growth", 1.0}
    }, {"ScenarioName", "Description", "DefaultMultiplier"})
in
    Source
```

### **B. Custom Multiplier Parameter Table (M Code)**

Create new blank query → Rename to "CustomMultiplier":

```m
let
    Source = Table.FromRows({
        {0.50}, {0.55}, {0.60}, {0.65}, {0.70}, {0.75}, {0.80}, {0.85}, {0.90}, {0.95},
        {1.00}, {1.05}, {1.10}, {1.15}, {1.20}, {1.25}, {1.30}, {1.35}, {1.40}, {1.45},
        {1.50}, {1.55}, {1.60}, {1.65}, {1.70}, {1.75}, {1.80}, {1.85}, {1.90}, {1.95}, {2.00}
    }, {"CustomMultiplierValue"})
in
    Source
```

---

## 🔧 **Step 3: Core DAX Measures**

### **Base Interpolation Measure**

```dax
GetInterpolatedValue = 
VAR SelectedInputType = SELECTEDVALUE('Parameters'[InputType])
VAR SelectedMonth = SELECTEDVALUE('DateTable'[Month])
RETURN 
    IF(
        ISBLANK(SelectedInputType) || ISBLANK(SelectedMonth),
        BLANK(),
        CALCULATE(
            MAX('InterpolatedInputs'[Value]),
            'InterpolatedInputs'[InputType] = SelectedInputType,
            'InterpolatedInputs'[Month] = SelectedMonth
        )
    )
```

### **Scenario Multiplier Measure**

```dax
ScenarioMultiplier = 
VAR SelectedScenario = SELECTEDVALUE('Scenarios'[ScenarioName])
VAR CustomValue = SELECTEDVALUE('CustomMultiplier'[CustomMultiplierValue])
RETURN 
    SWITCH(
        SelectedScenario,
        "Base", 1.0,
        "High_10", 1.1,
        "Low_10", 0.9,
        "High_25", 1.25,
        "Low_25", 0.75,
        "Custom", IF(ISBLANK(CustomValue), 1.0, CustomValue),
        1.0
    )
```

### **Account Measures (Scenario-Adjusted)**

```dax
TotalAccounts = 
VAR BaseAccounts = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "Accounts"
    )
VAR Multiplier = [ScenarioMultiplier]
RETURN BaseAccounts * Multiplier

ActiveAccounts = 
VAR TotalAccts = [TotalAccounts]
VAR ActiveShare = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "ActiveShare"
    )
RETURN TotalAccts * ActiveShare

CheckingAccounts = 
VAR ActiveAccts = [ActiveAccounts]
VAR CheckingShare = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "CheckingShare"
    )
RETURN ActiveAccts * CheckingShare

SavingsAccounts = 
VAR ActiveAccts = [ActiveAccounts]
VAR SavingsShare = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "SavingShare"
    )
RETURN ActiveAccts * SavingsShare
```

### **Transaction Volume Measures (Rates NOT affected by scenarios)**

```dax
ACHIncomingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR ACHInPerActive = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "ACHinPerActive"
    )
RETURN ActiveAccts * ACHInPerActive

ACHOutgoingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR ACHOutPerActive = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "ACHoutPerActive"
    )
RETURN ActiveAccts * ACHOutPerActive

RTPIncomingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR RTPInPerActive = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "RTPinPerActive"
    )
RETURN ActiveAccts * RTPInPerActive

RTPOutgoingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR RTPOutPerActive = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "RTPoutPerActive"
    )
RETURN ActiveAccts * RTPOutPerActive

WireIncomingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR WireInPerActive = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "WireInPerActive"
    )
RETURN ActiveAccts * WireInPerActive

WireOutgoingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR WireOutPerActive = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "WireOutPerActive"
    )
RETURN ActiveAccts * WireOutPerActive

DebitCardTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR DebitPerActive = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "DebitCardTransactionsPerActive"
    )
RETURN ActiveAccts * DebitPerActive
```

### **Revenue Measures (Rates NOT affected by scenarios)**

```dax
ACHIncomingRevenue = 
VAR Transactions = [ACHIncomingTransactions]
VAR Rate = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "ACHinRate"
    )
RETURN Transactions * Rate

ACHOutgoingRevenue = 
VAR Transactions = [ACHOutgoingTransactions]
VAR Rate = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "ACHoutRate"
    )
RETURN Transactions * Rate

RTPIncomingRevenue = 
VAR Transactions = [RTPIncomingTransactions]
VAR Rate = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "RTPinRate"
    )
RETURN Transactions * Rate

RTPOutgoingRevenue = 
VAR Transactions = [RTPOutgoingTransactions]
VAR Rate = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "RTPoutRate"
    )
RETURN Transactions * Rate

WireIncomingRevenue = 
VAR Transactions = [WireIncomingTransactions]
VAR Rate = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "WireInRate"
    )
RETURN Transactions * Rate

WireOutgoingRevenue = 
VAR Transactions = [WireOutgoingTransactions]
VAR Rate = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "WireOutRate"
    )
RETURN Transactions * Rate

DebitCardRevenue = 
VAR Transactions = [DebitCardTransactions]
VAR Rate = 
    CALCULATE(
        [GetInterpolatedValue],
        'InterpolatedInputs'[InputType] = "DebitCardTransactionRate"
    )
RETURN Transactions * Rate
```

### **Summary Measures**

```dax
TotalTransactionVolume = 
[ACHIncomingTransactions] + [ACHOutgoingTransactions] + 
[RTPIncomingTransactions] + [RTPOutgoingTransactions] + 
[WireIncomingTransactions] + [WireOutgoingTransactions] + 
[DebitCardTransactions]

TotalRevenue = 
[ACHIncomingRevenue] + [ACHOutgoingRevenue] + 
[RTPIncomingRevenue] + [RTPOutgoingRevenue] + 
[WireIncomingRevenue] + [WireOutgoingRevenue] + 
[DebitCardRevenue]

RevenuePerAccount = 
DIVIDE([TotalRevenue], [TotalAccounts], 0)

RevenuePerActiveAccount = 
DIVIDE([TotalRevenue], [ActiveAccounts], 0)
```

---

## 🎛️ **Step 4: Create Slicers**

### **On your report page, add these slicers:**

1. **Scenario Slicer**
   - Table: Scenarios
   - Field: ScenarioName
   - Type: Dropdown or List

2. **Custom Multiplier Slicer**
   - Table: CustomMultiplier  
   - Field: CustomMultiplierValue
   - Type: Slider
   - Only shows when "Custom" scenario is selected

3. **Month Slicer**
   - Table: DateTable (you'll need to create this)
   - Field: Month
   - Type: Slider (1 to 60)

---

## 📊 **Step 5: Create DateTable**

Create new blank query → Rename to "DateTable":

```m
let
    Source = List.Numbers(1, 60, 1),
    #"Converted to Table" = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Renamed Columns" = Table.RenameColumns(#"Converted to Table",{{"Column1", "Month"}}),
    #"Added Year" = Table.AddColumn(#"Renamed Columns", "Year", each Number.RoundUp([Month]/12)),
    #"Added MonthName" = Table.AddColumn(#"Added Year", "MonthName", each "Month " & Text.From([Month]))
in
    #"Added MonthName"
```

---

## ✅ **Implementation Order:**

1. ✅ **InterpolatedInputs table** (Step 1)
2. ✅ **Scenarios and CustomMultiplier tables** (Step 2)  
3. ✅ **DateTable** (Step 5)
4. ✅ **DAX measures** (Step 3)
5. ✅ **Report slicers** (Step 4)

---

## 🎯 **Benefits:**

- ✅ **Real-time scenario adjustment** with sliders
- ✅ **Custom scenarios** (0.5x to 2.0x multiplier)
- ✅ **Performance**: Base interpolation pre-calculated
- ✅ **Flexibility**: Easy to modify and extend
- ✅ **Correct logic**: Only accounts affected by scenarios

**Ready to start with Step 1 (InterpolatedInputs table)?**