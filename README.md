# Resident Evil 7: 21 — Card Game Solver

A terminal-based companion tool for the **21** card game from the *Resident Evil 7: Biohazard — Banned Footage Vol. 2* DLC. Tracks cards, computes odds, models opponent AI, and gives strategic advice in real time as you play.

BETA/WIP STILL MAKES MISTAKES
please report any issues you encounter!

## Requirements

- Python 3.6+
- No external dependencies — runs with the standard library only

## Quick Start

```bash
python3 re7_helper.py
```

## What It Does

The 21 minigame is a high-stakes blackjack variant where you draw from a shared deck of cards numbered 1–11 (no duplicates). Losing means torture. This solver helps you make optimal decisions by:

- **Tracking the deck** — Shows which of the 11 cards are still available vs. already played
- **Computing draw odds** — Exact probability of safe draws, busts, and perfect hits
- **Modeling opponent AI** — Simulates what the opponent will do based on their stay threshold, with built-in uncertainty when they haven't confirmed staying
- **Comparing STAY vs. HIT vs. FORCE DRAW vs. BUST** — Full probability breakdown for all four options, including intentional bust-to-win for challenge completion
- **Trump hand tracking** — Enter your held trump cards once, the solver remembers them across rounds, recommends which to play based on game state and enemy AI
- **Trump card mechanics** — Play Return/Remove/Exchange/Perfect Draw through the P menu and the solver handles the card movements
- **Opponent-specific warnings** — Alerts for dangerous trump cards like Curse, Dead Silence, Black Magic, Go for 17, Mind Shift+, and more
- **HP-aware advice** — Adjusts risk tolerance based on your remaining health
- **Challenge & unlock tracking** — Remembers which challenges you've completed and which trump cards you've unlocked, with contextual reminders during play
- **Save/load** — Challenge progress auto-saves to `~/.re7_21_progress.json` so you don't re-enter it every session

## Trump Card Database

All **37 trump cards** are catalogued across 8 categories: Bet modifiers (One Up through Twenty-One Up, Desire/Desire+), Defense (Shield, Shield+, Shield Assault/+), Card manipulation (Return, Remove, Exchange, Perfect Draw/+, Ultimate Draw, Love Your Enemy, Conjure), Target changers (Go for 17/24/27), Counter (Destroy/+/++), Trump draw (Trump Switch/+, Harvest, Happiness), Attack (Mind Shift/+, Curse, Black Magic, Dead Silence), and Special (Escape, Oblivion, Desperation). Press **T** during a fight to view the full reference.

## Supported Game Modes

| Mode | Opponents | Your HP | Opponent HP | Mechanic |
|------|-----------|---------|-------------|----------|
| **Normal 21** | Lucas (1 match, 3 rounds) | 10 | 10 | Tutorial — fingers, shock, saw |
| **Survival** | 5 Hoffmans | 5 (carries over) | 5 each | Finger-chopping |
| **Survival+** | 10 Hoffmans | 10 (carries over) | 10 each | Electric rig |

### Survival+ Opponent Structure

Opponents 1–4 and 6–9 are drawn randomly from a pool of variant types (each with sub-variants based on marking count). Two fights are always fixed:

- **Fight #5** — Molded Hoffman (mid-boss). Uses Curse, Black Magic, Conjure, Two Up, Destroy+, Go for 17.
- **Fight #10** — Undead Hoffman (final boss). Uses Ultimate Draw, Two Up+, Perfect Draw+, Dead Silence, Oblivion.
- **Mr. Big Head** — Rare random encounter with the Escape trump card.

Opponent variants by sack markings:

- **Tally marks** (vertical cuts, 2 or 3): One Up, Two Up, Happiness, Return, Desire, Mind Shift
- **Bloody handprints** (2 or 4 hands): Desire/Desire+, Mind Shift/Mind Shift+, Happiness. 4-hand variant is dangerous — Mind Shift+ takes ALL your trumps.
- **Barbed wire** (horizontal lines, 3 or 4): Shield, Shield Assault/+, Go for 17, Two Up
- **Cartoon mask** (Mr. Big Head): Escape only

Since the order is random, the tool asks you to identify each opponent by their markings.

## How to Use It During a Game

### 1. Challenge progress (on startup)

When you first launch, the solver asks which challenges you've already completed. This determines which trump cards you have access to — the solver will remind you to use unlocked cards like Perfect Draw+, Ultimate Draw, or Go for 27 when they'd help.

Press **U** from the main menu at any time to update your challenge progress.

### 2. Select your mode from the main menu

```
 1. Normal 21 (vs. Lucas — tutorial)
 2. Survival 21 (5-opponent gauntlet)
 3. Survival+ 21 (10-opponent hard gauntlet)
 4. Free Play (pick any opponent)
 C. Challenge Lab (priority unlock planner)
```

### 3. Fight loop

Each fight runs a loop of rounds. Within each round, the menu offers:

| Key | Action |
|-----|--------|
| **A** | **Analyze hand** — Enter your cards, opponent's visible cards, and dead cards. Gets advice + trump recommendations. |
| **P** | **Play a trump card** — Select from your hand. Handles Return/Remove/Exchange/target changes automatically. |
| **W** | **Edit trump hand** — Add or remove trump cards from your tracked hand. |
| **D** | **Done** — Record the round result (win/loss/tie/void) and damage dealt. |
| **G** | **Change target** — Set to 17, 21, 24, or 27 based on active "Go for X" trump. |
| **X** | **Dead cards** — View, add, or clear dead cards for this round. Resets each round (fresh deck). |
| **T** | Trump card reference (all 37 cards) |
| **I** | Opponent intel (trumps, AI type, tips) |
| **H** | Round history |
| **S** | HP status bars |
| **Q** | Quit fight |

### 4. Analyzing a hand

When you press **A**, you'll enter:

1. Your card values (e.g., `10 6`)
2. Opponent's visible cards (e.g., `8`)
3. Dead/removed cards — remembered within the round, resets next round
4. What did the opponent do?
   - **Enter** = nothing yet / still playing (default)
   - **2** = opponent stayed (done drawing) → hidden card is unknown, modeled as probability across remaining deck
   - **3** = you forced a draw → asks what card they drew, adds it to their total

The solver then shows:

- **Deck tracker** — Color-coded grid of which cards (1–11) are in or out
- **Draw table** — Every possible card you could draw and the resulting total
- **STAY vs. HIT vs. FORCE DRAW vs. BUST** — Full win/tie/loss breakdown for all options, including intentional bust-to-win odds
- **Action recommendation** — Picks the best option with reasoning
- **Unlocked trump hints** — When you're losing and have cards like Perfect Draw+ or Ultimate Draw unlocked, the solver reminds you
- **Bust challenge nudge** — When the bust-win challenge isn't completed yet and busting has decent odds, highlights the opportunity
- **Uncertainty note** — When opponent hasn't confirmed staying, reminds you that odds are estimates
- **Opponent-specific warnings** — Curse danger, Dead Silence risk, Go for 17 alerts, Mind Shift+ warnings, and more

### Example Output

```
 YOUR TOTAL: 16 (cards: [10, 6])
 OPPONENT VISIBLE: 8 (cards: [8])
 TARGET: 21
 SAFE HIT CHANCE: 71% (5/7 cards)

 If you draw:
  Card  1 → total 17 ✓
  Card  2 → total 18 ✓
  Card  3 → total 19 ✓
  Card  4 → total 20 ✓
  Card  5 → total 21 ✓ ★ PERFECT!
  Card  9 → total 25 ✖ BUST
  Card 11 → total 27 ✖ BUST

 MODEL: Opponent AI draws until 17+.
 (Opponent hasn't stayed — odds are estimates. Select '2' when they stop drawing.)
 If YOU STAY now  -> Win 91.3% | Tie 4.3% | Lose 4.3%.
 If YOU HIT now   -> Win 60.2% | Tie 5.1% | Lose 34.7% (Bust draw chance: 28.6%).
 If you FORCE A DRAW (Love Your Enemy) -> Win 55.8% | Tie 6.0% | Lose 38.2% (busts opponent: 29%).
 If you BUST ON PURPOSE -> Best card: 9 (total 25) → Win 12.5%. [Completes bust-win challenge!]
 UNLOCKED: You have Perfect Draw+ — guaranteed best card from the deck.
 ACTION: STAY — best win chance at 91.3% (+31.1% over next best).
```

### 5. Recording a round result

When you press **D**, just two inputs:

1. **Win / Loss / Tie / Void / Cancel** (1–5)
2. **How much damage was dealt?** (the bet number shown on screen, defaults to 1)

## "Go for X" — Target Changing

"Go for 17", "Go for 24", and "Go for 27" are trump cards that change the round target. Press **G** in the fight menu to set the current target (17 / 21 / 24 / 27). The solver handles this in two ways:

1. **Your odds update** — Bust threshold shifts to the new target. At target 24, cards that would bust you at 21 become safe draws. At target 17, cards above 17 bust you.
2. **Opponent AI adjusts** — The opponent's stay threshold shifts by the same amount (e.g., an opponent who normally stays at 17 will stay at 20 when target is 24, or at 13 when target is 17).

## Opponent AI Modeling

The solver models the opponent's behavior as a probability distribution. Two modes:

- **Opponent stayed** (option 2) — They stopped drawing but their hidden card is still face-down. The solver models every possible hidden card from the remaining deck as equally likely. For example, if 5 cards remain, each is a 20% chance of being their hidden card. Once both players stay, the round is over — just record the result with D.
- **Still playing** (default) — The solver estimates what the opponent will do based on their stay threshold, but bakes in uncertainty. Opponents near the target may gamble and draw again even past their threshold. **These odds are estimates — select '2' when they stop drawing for better accuracy.**

## Trump Hand Tracking

At the start of each fight, you can enter your held trump cards. The solver then:

- **Remembers your hand across rounds** within a fight (trump cards carry over between rounds in the game)
- **Recommends which trumps to play** based on the current game state during analysis (shows as "TRUMP CARD ADVICE" box)
- **Handles card mechanics** when you play them through the P menu — Return sends a card back to deck, Remove adds opponent's card to dead cards, Exchange swaps values, Go for X changes target automatically
- **Asks about changes** after editing — in case the opponent played trumps that affected your hand (Curse, Mind Shift, etc.)

The recommendation engine considers: whether you're busted (prioritizes Return/Go for X), enemy dangerous trumps (saves Destroy for Dead Silence/Black Magic/Curse), offensive opportunities (Love Your Enemy when bust odds are high), damage stacking (bet-ups on perfect hands), and defensive needs (Shield at low HP, Escape at critical HP).

## Save / Load

Challenge progress auto-saves to `~/.re7_21_progress.json` when you set it up. On next launch, it loads automatically — no need to re-enter which challenges you've completed or which trump cards you've unlocked. Press **U** from the main menu to update your progress (forces a re-prompt and saves).

## Challenge & Unlock Tracking

On startup, the solver asks which challenges you've already completed. This unlocks trump card reminders during play:

| Challenge | Reward |
|-----------|--------|
| Beat Normal 21 | Unlocks Survival mode |
| Beat Survival | Unlocks Survival+, **Perfect Draw+** |
| Beat Survival+ | Achievement |
| Win while bust | Starting Trump +1 |
| Use 15+ trumps in a round | **Trump Switch+** |
| Beat Survival with no damage | **Ultimate Draw** |
| Beat Survival+ with no damage | Grand Reward |
| Hit 21 three times in a row | **Go for 27** |
| Defeat opponent milestones | **Shield+**, **Two Up+**, **Go for 24** |

Bolded rewards are trump cards that the solver will remind you about during play. For example, if you've unlocked Perfect Draw+ and you're losing a hand, the solver will say "UNLOCKED: You have Perfect Draw+." If you're bust at 23 and you have Go for 27 unlocked, it'll tell you to switch targets.

The bust-to-win challenge is also integrated into normal play — the solver shows "INTENTIONAL BUST" as a 4th option alongside STAY/HIT/FORCE DRAW, with a nudge when you haven't completed it yet and the odds are decent.

Press **U** from the main menu to update your progress at any time.

## Challenge Lab

Press **C** from the main menu to access specialized tools for DLC challenges:

- **Bust-Win Planner** — Computes the best way to win a round while busted (both sides over target, closest wins). Shows odds for staying, forcing a random draw, or forcing the highest draw on the opponent.
- **15-Trump Planner** — Tracks progress toward using 15 trump cards in a single round for the Trump Switch+ unlock.
- **No-Damage Blueprint** — Strategy guide for completing Survival and Survival+ without taking any damage.

## Opponent Database

Every opponent variant is catalogued with:

- **AI type** and stay threshold
- **Unique trump cards** and what they actually do (corrected from wiki sources)
- **Counter-strategies** for each dangerous trump
- **Sub-variant info** (e.g., 2-hand vs. 4-hand Bloody Handprints)

The data is sourced from the [RE Wiki](https://residentevil.fandom.com/wiki/21), [RE Wiki — Hoffman](https://residentevil.fandom.com/wiki/Hoffman), community guides, and video walkthroughs.

## Tips

- **Card count every round.** The deck is only 11 cards with no duplicates. Knowing what's left is the single biggest advantage you have.
- **Save Destroy cards** for the most dangerous opponent trumps (Dead Silence, Black Magic, Curse, Escape, Shield Assault+).
- **Don't hoard trumps** against Bloody Handprints Hoffman — Desire/Desire+ punishes you for holding them.
- **Watch for Go for 17** — Barbed Wire and Molded Hoffman use it. Your 20 becomes a bust.
- **Mark when the opponent stays (option 2).** This switches from guessing their behavior to modeling their hidden card. Use option 4 when the round ends and cards are revealed for exact numbers.
- **Dead cards reset each round.** The deck is fresh every round — Destroy only removes a card for that round.
- **Go for the bust-win challenge early.** The solver shows you when busting on purpose has decent win odds. Completing it gives you an extra starting trump card every round.
- **Set your challenge progress on startup.** The solver uses this to remind you about unlocked trump cards you might forget about during intense fights.
- **The solver is a guide.** It models the opponent as a probability distribution, but the actual game AI can behave unpredictably, especially in Survival+.
