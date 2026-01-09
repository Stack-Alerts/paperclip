# Improved ML Training Strategy - Based on Validation Findings

## 🎯 Problem Analysis

### Current Model Issues:
1. **93.6% pattern accuracy → 33.5% outcome accuracy** (60% gap!)
2. **Win rate only 63.7%** (good but not great)
3. **Direction accuracy only 13.5%** (poor at predicting strong moves)
4. **Trained on patterns that don't strongly predict profits**

### What Works:
- ✅ Short trades: 68.2% win rate, 0.504% avg return
- ✅ Model is profitable (just not optimal)
- ✅ 165k trade opportunities (good signal frequency)

---

## 🚀 OPTIMAL TRAINING STRATEGY

### Strategy 1: Train on Outcome-Based Labels (RECOMMENDED)

**Concept:** Train model to predict actual profitable outcomes, not patterns

**Implementation:**
```python
# Use outcome-based ground truth as labels
X = features  # Same 115 features
y = outcome_labels  # -1, 0, 1 based on actual 8hr outcomes

# Only train on high-confidence outcomes
confident_mask = (outcome_confidence >= 0.8)
X_train = X[confident_mask]
y_train = y[confident_mask]
```

**Expected Results:**
- Lower trade frequency (only ~37k opportunities vs 165k)
- **Much higher win rate** (80%+ based on outcome-based simulation)
- **Higher avg return** (3.576% vs 0.399%)
- Better profit factor

**Trade-off:**
- Fewer trades → need longer holding periods
- More selective → miss some smaller moves
- **But:** Each trade more reliable

---

### Strategy 2: Hybrid Ensemble Model (BEST OF BOTH WORLDS)

**Concept:** Combine pattern prediction + outcome prediction

```python
# Model 1: Pattern predictor (current model)
model_pattern = XGBoost(trained_on=pattern_labels)  # 93.6% accurate, 63.7% win rate

# Model 2: Outcome predictor (new)
model_outcome = XGBoost(trained_on=outcome_labels)  # High confidence, fewer trades

# Ensemble: Only trade when BOTH agree
final_prediction = model_pattern.predict() if model_outcome.confidence > 0.8 else NEUTRAL

# Or weighted approach
final_prediction = (0.3 * model_pattern + 0.7 * model_outcome)
```

**Expected Results:**
- Medium trade frequency (~60k-80k trades)
- Higher win rate (75%+)
- Better avg return (1-2%)
- Best of both: frequency + accuracy

---

### Strategy 3: Gradient Boosting with Custom Loss Function

**Concept:** Optimize for profit, not just classification accuracy

```python
def profit_loss(y_true, y_pred):
    """
    Custom loss that penalizes wrong direction predictions more heavily.
    Rewards correct strong predictions more than correct weak predictions.
    """
    # Get actual outcomes
    actual_returns = outcome_final_change_pct
    
    # Predicted direction
    pred_direction = y_pred
    
    # If predicted bullish but actually bearish → huge penalty
    wrong_direction = (pred_direction * actual_returns < 0)
    penalty = wrong_direction * abs(actual_returns) * 10
    
    # If predicted correctly → reward proportional to return
    correct_direction = (pred_direction * actual_returns > 0)
    reward = correct_direction * abs(actual_returns)
    
    return penalty - reward

model = XGBClassifier(objective=profit_loss)
```

**Expected Results:**
- Optimizes for $ profit, not accuracy
- Should naturally learn to avoid costly mistakes
- Focus on high R:R opportunities

---

### Strategy 4: Multi-Target Learning

**Concept:** Predict multiple targets simultaneously

```python
# Train model to predict 3 things:
# 1. Direction (bearish/neutral/bullish)
# 2. Magnitude (how much it will move)
# 3. Confidence (probability of correct prediction)

targets = {
    'direction': trend_label,           # -1, 0, 1
    'magnitude': abs(final_change_pct), # 0-10%
    'confidence': outcome_confidence    # 0-1
}

# Multi-output model
model = MultiOutputXGBClassifier()
model.fit(X, targets)

# Trade only on high confidence + high magnitude predictions
trade_signal = (
    model.predict_confidence() > 0.8 AND
    model.predict_magnitude() > 2.0
)
```

**Expected Results:**
- More nuanced predictions
- Can size positions based on magnitude
- Filter low-confidence trades
- Target win rate: 75%+

---

## 📊 Recommended Implementation Plan

### Phase 1: Quick Win - Outcome-Based Training (2-3 hours)

**Step 1: Retrain on outcome labels**
```bash
python3 train_layer05_outcome_based.py
```

**What it does:**
- Uses outcome_labels instead of pattern_labels
- Same 115 features
- Filters to high-confidence samples only
- Expects: Higher win rate, fewer trades

**Success criteria:**
- Win rate > 75%
- Avg return > 2%
- Profit factor > 3.0

---

### Phase 2: Hybrid Ensemble (4-6 hours)

**Step 1: Keep current pattern model**
**Step 2: Train new outcome model**
**Step 3: Create ensemble predictor**

```python
def ensemble_predict(features):
    pattern_pred = model_pattern.predict(features)
    outcome_pred = model_outcome.predict(features)
    outcome_conf = model_outcome.predict_proba(features).max()
    
    # Only trade if:
    # 1. Outcome model is confident (>80%)
    # 2. Both models agree on direction
    if outcome_conf > 0.8 and pattern_pred == outcome_pred:
        return outcome_pred
    else:
        return 0  # neutral - don't trade
```

**Success criteria:**
- Win rate > 70%
- Avg return > 1.5%
- Trade frequency > 50k
- Profit factor > 2.5

---

### Phase 3: Advanced - Custom Loss Function (8-10 hours)

**Step 1: Implement profit-optimized loss**
**Step 2: Retrain with new objective**
**Step 3: Validate against outcomes**

**Success criteria:**
- Win rate > 75%
- Profit factor > 3.0
- Sharpe ratio > 2.0

---

## 🔥 IMMEDIATE ACTION ITEM

### Create `train_layer05_outcome_based.py`

This will retrain on actual outcomes instead of patterns:

```python
"""
Train Layer 0.5 ML Model on OUTCOME-BASED Labels

Instead of training on technical pattern labels,
train on what ACTUALLY happened profitably.
"""

import pandas as pd
from pathlib import Path
import joblib
import json
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Load outcome-based ground truth
outcome_gt = pd.read_csv('data/processed/15m_ground_truth_outcome_based.csv')
outcome_gt['datetime'] = pd.to_datetime(outcome_gt['datetime'])

# Load features
features_df = pd.read_parquet('data/processed/layer05_features_final.parquet')
features_df['datetime'] = pd.to_datetime(features_df['datetime'])

# Merge
merged = features_df.merge(outcome_gt, on='datetime', how='inner')

# Filter to HIGH CONFIDENCE outcomes only
# This ensures we train on clear, profitable moves
confident = merged[merged['confidence'] >= 0.8].copy()

print(f"Training on {len(confident):,} high-confidence samples")
print(f"Removed {len(merged) - len(confident):,} low-confidence samples")

# Prepare data
feature_cols = [col for col in features_df.columns if col != 'datetime' and col != 'trend_label']
X = confident[feature_cols].values
y = confident['trend_label'].values + 1  # Convert -1,0,1 to 0,1,2

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scale
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train with optimized parameters
model = XGBClassifier(
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='multi:softmax',
    num_class=3,
    random_state=42,
    eval_metric='mlogloss'
)

# Fit
print("Training outcome-based model...")
model.fit(
    X_train_scaled, y_train,
    eval_set=[(X_test_scaled, y_test)],
    early_stopping_rounds=50,
    verbose=50
)

# Save
output_dir = Path('data/models/layer05_ml_outcome_based')
output_dir.mkdir(parents=True, exist_ok=True)

joblib.dump(model, output_dir / 'xgboost_model.pkl')
joblib.dump(scaler, output_dir / 'scaler.pkl')

with open(output_dir / 'features.json', 'w') as f:
    json.dump({'features': feature_cols}, f)

print(f"✅ Outcome-based model saved to {output_dir}")
```

---

## 📈 Expected Improvements

### Current Model:
- Pattern accuracy: 93.6%
- Outcome accuracy: 33.5%
- Win rate: 63.7%
- Avg return: 0.399%
- Trades: 165k

### Outcome-Based Model (Projected):
- Pattern accuracy: ~50% (will be lower on patterns)
- Outcome accuracy: 85%+ (trained for this!)
- Win rate: 80%+
- Avg return: 2-3%
- Trades: ~40k

### Hybrid Model (Projected):
- Pattern accuracy: ~75%
- Outcome accuracy: 60%+
- Win rate: 75%
- Avg return: 1.5-2%
- Trades: ~80k

---

## 🎯 Which Strategy to Use?

### For Maximum Profit per Trade:
→ **Strategy 1: Outcome-Based Training**
- Best win rate
- Best avg return
- Fewer but better trades

### For Maximum Total Profit:
→ **Strategy 2: Hybrid Ensemble**
- Good win rate
- Good trade frequency
- Best overall returns

### For Cutting-Edge Performance:
→ **Strategy 3: Custom Loss Function**
- Directly optimizes for $
- Most sophisticated
- Requires more dev time

---

## 💡 Key Insight

The problem isn't the features or the algorithm. **It's what we're teaching the model.**

- Current: "Learn to match technical patterns" → 93.6% accurate but only 63.7% profitable
- Better: "Learn to predict profitable outcomes" → Lower pattern accuracy but 80%+ profitable

**We should train on what makes money, not what looks like a pattern.**

---

## 🚀 Next Steps

1. **Immediate:** Create and run `train_layer05_outcome_based.py`
2. **Validate:** Test new model with profit simulation
3. **Compare:** Old vs new vs hybrid
4. **Deploy:** Best performing model

**Ready to implement?** Say the word and I'll create the improved training script.
