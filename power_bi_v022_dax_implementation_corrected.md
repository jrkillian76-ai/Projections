# Power BI v0.22 DAX Implementation - CORRECTED
## Scenarios Only Affect Accounts, Not Other Variables

**IMPORTANT CORRECTION**: Scenarios should only modify the **Accounts** input type. All other variables (rates, fees, transaction volumes per active account, etc.) remain unchanged across scenarios.

---

## 🏗️ 1. BASE MEASURES - Interpolation Engine

### Primary Interpolation Measure (Base Values Only)
```dax
// Base interpolation for any input type and month - NO SCENARIO ADJUSTMENT
GetInterpolatedValue = 
VAR SelectedInputType = SELECTEDVALUE('Parameters'[InputType])
VAR SelectedMonth = SELECTEDVALUE('DateTable'[Month])

// Get key month values from Parameters table
VAR M1Value = CALCULATE(MAX('Parameters'[Value]), 'Parameters'[InputType] = SelectedInputType, 'Parameters'[Month] = 1)
VAR M6Value = CALCULATE(MAX('Parameters'[Value]), 'Parameters'[InputType] = SelectedInputType, 'Parameters'[Month] = 6)
VAR M12Value = CALCULATE(MAX('Parameters'[Value]), 'Parameters'[InputType] = SelectedInputType, 'Parameters'[Month] = 12)
VAR M24Value = CALCULATE(MAX('Parameters'[Value]), 'Parameters'[InputType] = SelectedInputType, 'Parameters'[Month] = 24)
VAR M36Value = CALCULATE(MAX('Parameters'[Value]), 'Parameters'[InputType] = SelectedInputType, 'Parameters'[Month] = 36)

// Interpolate based on selected month - NO SCENARIO MULTIPLIER
VAR BaseValue = 
    SWITCH(
        TRUE(),
        SelectedMonth = 1, M1Value,
        SelectedMonth <= 6, M1Value + (M6Value - M1Value) * (SelectedMonth - 1) / 5,
        SelectedMonth <= 12, M6Value + (M12Value - M6Value) * (SelectedMonth - 6) / 6,
        SelectedMonth <= 24, M12Value + (M24Value - M12Value) * (SelectedMonth - 12) / 12,
        SelectedMonth <= 36, M24Value + (M36Value - M24Value) * (SelectedMonth - 24) / 12,
        // Beyond month 36, apply growth rate
        VAR GrowthRate = CALCULATE(MAX('Parameters'[Value]), 'Parameters'[InputType] = "GrowthRateM37Plus", 'Parameters'[Month] = 37)
        RETURN M36Value * POWER(1 + GrowthRate, SelectedMonth - 36)
    )

RETURN BaseValue
```

### Scenario-Adjusted Accounts Only
```dax
// Accounts with scenario adjustment - ONLY for Accounts input type
GetAccountsWithScenario = 
VAR SelectedMonth = SELECTEDVALUE('DateTable'[Month])
VAR SelectedScenario = IF(ISBLANK(SELECTEDVALUE('Scenarios'[ScenarioName])), "Base", SELECTEDVALUE('Scenarios'[ScenarioName]))

// Get base accounts value using the interpolation measure
VAR BaseAccounts = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "Accounts"
    )

// Apply scenario multiplier ONLY to accounts
VAR ScenarioMultiplier = 
    SWITCH(
        SelectedScenario,
        "Base", 1.0,
        "High_10", 1.1,
        "Low_10", 0.9,
        "High_25", 1.25,
        "Low_25", 0.75,
        "Custom", RELATED('ScenarioParameters'[CustomMultiplier]),
        1.0
    )

RETURN BaseAccounts * ScenarioMultiplier
```

---

## 🏦 2. ACCOUNT CALCULATIONS

### Total Accounts (Scenario-Adjusted)
```dax
TotalAccounts = [GetAccountsWithScenario]
```

### Active Accounts
```dax
ActiveAccounts = 
VAR TotalAccts = [TotalAccounts]
VAR ActiveShareValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "ActiveShare"
    )

RETURN TotalAccts * ActiveShareValue
```

### Checking Accounts
```dax
CheckingAccounts = 
VAR ActiveAccts = [ActiveAccounts]
VAR CheckingShareValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "CheckingShare"
    )

RETURN ActiveAccts * CheckingShareValue
```

### Savings Accounts
```dax
SavingsAccounts = 
VAR ActiveAccts = [ActiveAccounts]
VAR SavingsShareValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "SavingShare"
    )

RETURN ActiveAccts * SavingsShareValue
```

---

## 💳 3. TRANSACTION VOLUME CALCULATIONS (Rates Unchanged by Scenarios)

### ACH Incoming Transactions
```dax
ACHIncomingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR ACHInPerActiveValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "ACHinPerActive"
    )

RETURN ActiveAccts * ACHInPerActiveValue
```

### ACH Outgoing Transactions
```dax
ACHOutgoingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR ACHOutPerActiveValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "ACHoutPerActive"
    )

RETURN ActiveAccts * ACHOutPerActiveValue
```

### RTP Incoming Transactions
```dax
RTPIncomingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR RTPInPerActiveValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "RTPinPerActive"
    )

RETURN ActiveAccts * RTPInPerActiveValue
```

### RTP Outgoing Transactions
```dax
RTPOutgoingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR RTPOutPerActiveValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "RTPoutPerActive"
    )

RETURN ActiveAccts * RTPOutPerActiveValue
```

### Wire Incoming Transactions
```dax
WireIncomingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR WireInPerActiveValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "WireInPerActive"
    )

RETURN ActiveAccts * WireInPerActiveValue
```

### Wire Outgoing Transactions
```dax
WireOutgoingTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR WireOutPerActiveValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "WireOutPerActive"
    )

RETURN ActiveAccts * WireOutPerActiveValue
```

### Debit Card Transactions
```dax
DebitCardTransactions = 
VAR ActiveAccts = [ActiveAccounts]
VAR DebitPerActiveValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "DebitCardTransactionsPerActive"
    )

RETURN ActiveAccts * DebitPerActiveValue
```

---

## 💰 4. REVENUE CALCULATIONS (Rates Unchanged by Scenarios)

### ACH Incoming Revenue
```dax
ACHIncomingRevenue = 
VAR Transactions = [ACHIncomingTransactions]
VAR RateValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "ACHinRate"
    )

RETURN Transactions * RateValue
```

### ACH Outgoing Revenue
```dax
ACHOutgoingRevenue = 
VAR Transactions = [ACHOutgoingTransactions]
VAR RateValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "ACHoutRate"
    )

RETURN Transactions * RateValue
```

### RTP Incoming Revenue
```dax
RTPIncomingRevenue = 
VAR Transactions = [RTPIncomingTransactions]
VAR RateValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "RTPinRate"
    )

RETURN Transactions * RateValue
```

### RTP Outgoing Revenue
```dax
RTPOutgoingRevenue = 
VAR Transactions = [RTPOutgoingTransactions]
VAR RateValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "RTPoutRate"
    )

RETURN Transactions * RateValue
```

### Wire Incoming Revenue
```dax
WireIncomingRevenue = 
VAR Transactions = [WireIncomingTransactions]
VAR RateValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "WireInRate"
    )

RETURN Transactions * RateValue
```

### Wire Outgoing Revenue
```dax
WireOutgoingRevenue = 
VAR Transactions = [WireOutgoingTransactions]
VAR RateValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "WireOutRate"
    )

RETURN Transactions * RateValue
```

### Debit Card Revenue
```dax
DebitCardRevenue = 
VAR Transactions = [DebitCardTransactions]
VAR RateValue = 
    CALCULATE(
        [GetInterpolatedValue],
        'Parameters'[InputType] = "DebitCardTransactionRate"
    )

RETURN Transactions * RateValue
```

---

## 📊 5. SUMMARY MEASURES

### Total Transaction Volume
```dax
TotalTransactionVolume = 
[ACHIncomingTransactions] + [ACHOutgoingTransactions] + 
[RTPIncomingTransactions] + [RTPOutgoingTransactions] + 
[WireIncomingTransactions] + [WireOutgoingTransactions] + 
[DebitCardTransactions]
```

### Total Revenue
```dax
TotalRevenue = 
[ACHIncomingRevenue] + [ACHOutgoingRevenue] + 
[RTPIncomingRevenue] + [RTPOutgoingRevenue] + 
[WireIncomingRevenue] + [WireOutgoingRevenue] + 
[DebitCardRevenue]
```

### Revenue Per Account
```dax
RevenuePerAccount = 
DIVIDE([TotalRevenue], [TotalAccounts], 0)
```

### Revenue Per Active Account
```dax
RevenuePerActiveAccount = 
DIVIDE([TotalRevenue], [ActiveAccounts], 0)
```

---

## 🎯 6. SCENARIO HELPER MEASURES

### Current Scenario
```dax
CurrentScenario = 
IF(
    ISBLANK(SELECTEDVALUE('Scenarios'[ScenarioName])),
    "Base",
    SELECTEDVALUE('Scenarios'[ScenarioName])
)
```

### Scenario vs Base Variance
```dax
ScenarioVariance = 
VAR CurrentRevenue = [TotalRevenue]
VAR BaseRevenue = 
    CALCULATE(
        [TotalRevenue],
        'Scenarios'[ScenarioName] = "Base"
    )

RETURN CurrentRevenue - BaseRevenue
```

### Scenario vs Base Percentage
```dax
ScenarioVariancePercent = 
VAR CurrentRevenue = [TotalRevenue]
VAR BaseRevenue = 
    CALCULATE(
        [TotalRevenue],
        'Scenarios'[ScenarioName] = "Base"
    )

RETURN DIVIDE(CurrentRevenue - BaseRevenue, BaseRevenue, 0)
```

---

## 🔧 7. HELPER TABLES (M Code for Power Query)

### DateTable M Code
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

### Scenarios Table M Code
```m
let
    Source = Table.FromRows({
        {"Base", 1.0, "Base case scenario"},
        {"High_10", 1.1, "+10% account growth scenario"},
        {"Low_10", 0.9, "-10% account growth scenario"},
        {"High_25", 1.25, "+25% account growth scenario"},
        {"Low_25", 0.75, "-25% account growth scenario"},
        {"Custom", 1.0, "Custom adjustable account growth scenario"}
    }, {"ScenarioName", "DefaultMultiplier", "Description"})
in
    Source
```

---

## 📝 Key Changes Made

### ✅ **What Changed:**
1. **`GetInterpolatedValue`**: Removed scenario logic - now returns pure base values
2. **`GetAccountsWithScenario`**: New measure that only applies scenarios to Accounts
3. **All other measures**: Use `GetInterpolatedValue` directly (no scenario adjustment)
4. **Account measures**: Use `GetAccountsWithScenario` as the foundation

### ✅ **Scenario Behavior:**
- **Base**: 1,000 → 20,000 → 60,000 → 120,000 → 200,000 accounts
- **High_10**: 1,100 → 22,000 → 66,000 → 132,000 → 220,000 accounts  
- **Low_10**: 900 → 18,000 → 54,000 → 108,000 → 180,000 accounts
- **All rates/fees**: Unchanged across scenarios

### ✅ **Result:**
- Transaction volumes scale with account changes
- Revenue scales proportionally 
- Rates, fees, and per-account metrics remain constant
- Scenario impact is purely from account growth differences

This corrected implementation ensures scenarios only affect account growth, while all other business parameters remain stable across scenarios!