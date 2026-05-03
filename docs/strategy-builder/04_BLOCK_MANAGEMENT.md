# Block Management System - Strategy Builder
**Document**: 04_BLOCK_MANAGEMENT.md  
**Status**: 🟢 Complete  
**Priority**: P0 - Critical

## Block Management Overview

The Block Management System handles all operations related to adding, organizing, and removing building blocks within a strategy.

## Core Operations

### 1. Add Block
**Trigger**: User selects block from search results
**Process**:
1. Validate block not already added
2. Show AND/OR selection modal
3. Add block to strategy configuration
4. Remove from available blocks list  
5. Auto-select first signal
6. Update required signal count if AND
7. Trigger real-time preview update

### 2. Move Block Up/Down
**Controls**: ▲▼ buttons on each block
**Logic**:
- Cannot move first block up
- Cannot move last block down
- Maintains dependency integrity
- Re-validates timing constraints after move
- Updates preview

### 3. Indent/Unindent Block
**Controls**: →← buttons
**Purpose**: Visual dependency indication
**Rules**:
- Cannot indent first block
- Indented block depends on previous block
- Affects signal count calculation
- Visual: Adds left margin + connection line

### 4. Remove Block
**Process**:
1. Check for dependent blocks
2. Show warning if dependencies exist
3. Offer cascade removal
4. Return block to available list
5. Recalculate signal requirements
6. Update preview

### 5. Reorder via Drag-and-Drop
**Implementation**: HTML5 Drag & Drop API or library
**Features**:
- Visual drag indicator
- Drop zones between blocks
- Smooth animations
- Dependency preservation
- Auto-scroll if needed

## Block State Management

```python
class BlockManager:
    def __init__(self, registry, config_engine):
        self.registry = registry
        self.config = config_engine
        self.selected_blocks = []
        
    def add_block(self, block_name: str, logic: str):
        # Validate and add
        if block_name in [b.name for b in self.selected_blocks]:
            raise ValueError("Block already added")
        
        metadata = self.registry.get_block(block_name)
        block = BlockInstance(
            name=block_name,
            logic=logic,
            metadata=metadata,
            signals=[metadata.valid_signals[0]]  # Default first signal
        )
        
        self.selected_blocks.append(block)
        self.config.recalculate_requirements()
        
    def move_block(self, from_idx: int, to_idx: int):
        block = self.selected_blocks.pop(from_idx)
        self.selected_blocks.insert(to_idx, block)
        self.validate_dependencies()
        
    def indent_block(self, idx: int):
        if idx == 0:
            raise ValueError("Cannot indent first block")
        self.selected_blocks[idx].indented = True
        self.selected_blocks[idx].depends_on = self.selected_blocks[idx-1]
```

## Visual Representation

```
[Block 1: Double Top] (AND) ▲▼ ×
  └─ BEARISH_BREAKDOWN [AND] [Within 20 candles]

  [Block 2: Volume Spike] (AND) ▲▼ →← ×
    └─ HIGH_VOLUME [AND]
    
    [Block 3: RSI] (OR) ▲▼ →← ×
      └─ OVERBOUGHT [OR]
```

**Version**: 1.0
