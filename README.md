# Resident Evil 7: 21 — Card Game Solver

A terminal companion for the **21** card game from *Resident Evil 7: Biohazard — Banned Footage Vol. 2*.
It tracks the round, works out exact draw and win odds, models each Hoffman's behaviour, and gives
trump-card and challenge advice as you play. It's one Python file with no dependencies, so it works
next to any platform's copy of the game (PC, console or cloud).

---

## Project status

Using REFramework, I can deduce the actual 21 game rules (trumps, damage, AI behavior) and build the tool to be extremely close to or replicate the in-game logic.
What I won't ship publicly is a solution that requires tracing/instrumentation to reconstruct RNG state or seeds — because that only guarantees perfect prediction on PC, and this tool was meant to help console/all players.
If it turns out the game uses a fixed, in-game-deducible seed (something you can determine without special tools), or a random seed every time, I'll revisit a public release. Otherwise, the tool is a rules-accurate simulator + probability/strategy solver rather than a perfect "next card" predictor.
If anyone wants to continue and publish their own build using my work as a base, please give credit.

The current build is on `main` (the old `Sigh` branch was merged). So far, no RNG state has been found.

---

## Quick start

You need **Python 3.6+**. Download `re7_helper_latest.py` and `hoffman_rule_table.json` into the same folder, then:

```bash
python3 re7_helper_latest.py
```

That opens the interactive solver (menus, below). For a one-off question, use **quick odds**:

```bash
python3 re7_helper_latest.py odds --me 10 5 2 --opp 11 7 --ai tally_basic
```

On Windows, use `py` instead of `python3`.

---

## Quick odds (`odds`)

Type in the cards you can see and get the exact numbers. No menus, nothing is saved.

| Option | Meaning |
|---|---|
| `--me N N ...` | **All** your cards (face-down + face-up). Required. |
| `--opp N ...` | The opponent's **face-up** cards. |
| `--opp-hidden N` | The opponent's face-down card, if you know it (for example, your `4 Card` failed, so they hold the 4). |
| `--dead N ...` | Cards removed from play this round (for example, by **Remove**). |
| `--target 17/21/24/27` | Active target while a *Go For* trump is on the table. Default: 21. |
| `--stayed` | The opponent has stopped drawing. |
| `--ai NAME` | Opponent AI profile: `generic` (default), `tally_basic`, `bloody_survival`, `barbed_survival`, `mr_big_head`, `molded_mid`, `molded_final`, … (`odds --help` lists them all). |

**Example:** you're on 17, and Hoffman shows 11 + 7 with one hidden card.

```
$ python3 re7_helper_latest.py odds --me 10 5 2 --opp 11 7 --ai tally_basic
You: 17  [2, 5, 10]   Opponent showing: 18  [11, 7] + 1 hidden card
Target 21   Unseen cards: [1, 3, 4, 6, 8, 9]
Opponent model: still drawing — Draws below 16 | Satisfied at 18+

Next draw: 50% safe, 50% bust, perfect 21 with [4]
  STAY now  -> win  66.7%  tie   0.0%  lose  33.3%
  HIT once  -> win  53.3%  tie   6.7%  lose  40.0%

If the target changed (Go for 17 / 24 / 27):
  target  safe   stay-win  hit-win
      17     0%    100.0%    50.0%
      21    50%     66.7%    53.3% <- now
      24    67%     33.3%    46.7%
      27   100%      0.0%    43.3%

```

Staying wins two times in three here. Hoffman already shows 18, so 4 of the 6 cards he could be hiding put him over 21.
The last table shows what playing (or facing) a *Go For* card would do to the same hand.

---

## Interactive solver

### Modes

| Menu | Mode | Opponents | Your HP | Opponent HP | What the solver does |
|---|---|---|---|---|---|
| 1 | **Normal 21** | Lucas (3 rounds: fingers → shock → saw) | 10 | 10 | Tutorial. Normal odds and advice. In the scripted saw round it switches to fixed survival steps (see below). |
| 2 | **Survival** | 5 Hoffmans in a row | 5 (carries over) | 5 each | Gauntlet. Tracks HP across fights and warns you to save strong trumps for the last fight. |
| 3 | **Survival+** | 10 Hoffmans in a row | 10 (carries over) | 10 each | Same, but harder. Fight #5 is always Molded Hoffman (mid-boss) and fight #10 is always Undead Hoffman (final boss). The other fights are drawn from the variant pools (Tally Marks, Bloody Handprints, Barbed Wire, Mr. Big Head). You pick the variant from its visual markings. |
| 4 | **Free Play** | Any opponent | you choose | you choose | Practise against, or analyse, a single opponent. |
| R | Trump reference | — | — | — | Every trump card and its effect. |
| U | Challenge progress | — | — | — | Mark which challenges you've completed. This changes which trumps the solver assumes you can have. Progress is saved to `~/.re7_21_progress.json`. |

**Lucas, saw round:** Lucas is scripted to play **Desperation** (bets go to 100 and draws are locked) and **Perfect Draw** (he hits 21).
The counter is to hold **Love Your Enemy** and play it once he's on 21. It hands him his "best" card, and on 21 every card busts him.
The solver gives these steps instead of normal odds for that round.

### During a fight

After you enter your face-down card, your face-up card and the opponent's face-up card, the board updates after every action:

| Key | Action |
|---|---|
| `H` | You drew a card |
| `O` | Opponent drew a card |
| `S` | Opponent stays (the model switches to "hidden card only") |
| `I` | Enemy played a trump: walks you through its effect (bets, target, Remove → dead card, …) |
| `P` | You played a trump: applies it (Go For target, Exchange, Return, numbered cards, …). A failed `N Card` draw tells the solver the opponent's hidden card. |
| `D` | Resolve the round (enter the opponent's hidden card, or the result and damage) |
| `?` | Tools: `W` edit trump hand, `X` dead cards, `T` trump reference, `F` opponent info, `G` round history, `V` HP, `B` bust-win challenge guide |
| `Q` | Quit the fight |

Each board shows:
- your safe / bust chance and which cards give exactly the target
- win / tie / lose % if you **stay** now, **hit** once, **force a draw** with Love Your Enemy (if you hold it), or **bust on purpose** (bust-win challenge)
- a single **ACTION** line. It goes with the best win % unless two options are within 5 points; in that case it uses tiebreak rules (HP, safe %, perfect cards).
- warnings about the opponent's trumps (Curse, Dead Silence, Go for 17, …) and a likely-next-enemy-trump prediction from `hoffman_rule_table.json`
- trump-play suggestions that take into account HP and whether the fight is a boss (it saves strong cards for fights #5 and #10)

### Dead cards

A **dead card** is a value that can't be drawn again this round, for example a card taken out of play by **Remove**.
Dead cards are removed from the deck odds and reset every round. If you miss an input (especially an enemy draw or return), the odds will drift, so keep the board in sync.

---

## How the odds are calculated

- **Cards you can't see** = 1–11, minus your hand, the opponent's face-up cards, dead cards and (if known) their hidden card.
  One of those unseen values is the opponent's **face-down card**. The rest are the deck.
- **Your next draw:** every unseen value is equally likely. The hidden card is equally likely to be any of them, so this is exact.
- **The opponent's final total:** the solver adds the hidden card (it's always there), then lets the opponent draw according to its **AI profile**. For each total, the profile gives the chance it draws (always below one threshold, never at or above another, and in between it depends on your visible hand).
  It works through every possible card order exactly. Only the AI profile is an estimate. The card maths isn't.
- **Love Your Enemy / Perfect Draw** give the *best possible card*: the largest card that doesn't bust, or the smallest card if every card busts.
- **Stay vs hit** compares standing now with taking exactly one more card and then standing.

The test suite checks all of this against a separate, deliberately naive brute force that plays out every ordering of the unseen cards (see *Tests*).

---

## Rules & sources

| Rule used by the solver | Source |
|---|---|
| One shared 11-card deck, 1–11, no duplicates | TheGamer, [*How To Beat Hoffman In 21*](https://www.thegamer.com/resident-evil-7-21-blackjack-guide/): "a single 11 card deck that both Clancy and Hoffman share", "there are no doubles in the deck" |
| Closest to the target without going over wins | Same guide ("get as close to 21 as possible without going over") |
| *Go For* trumps change the target (17 / 24 / 27) | Same guide for Go For 24 ("raises the target number from 21"); 17 and 27 from the author's trump list (`TRUMPS` in the script) |
| Love Your Enemy gives the opponent the best card in the deck | Same guide ("granting Hoffman the best card in the deck") |
| Perfect Draw gives the best possible card | Author's trump list (`TRUMPS`). "Best" is read as: the largest card that doesn't bust, or the smallest card if every card busts (the solver's interpretation; it also applies to Love Your Enemy). |
| Lucas finger round: on a tie, *both* lose a finger | Same guide ("Ties result in both Clancy and Hoffman losing their fingers"). The solver's result screen records a tie as no damage, so log that round manually. |
| Each player holds one face-down card plus face-up cards | Author's in-game testing |
| If **both** bust, the lower total wins (tie if equal) | Author's in-game testing. Needed for the "win while bust" challenge. |
| Opponent AI thresholds, trump timing, per-opponent kits | Author's REFramework analysis of the game's `CardGameBanker` / `CardGameCondition` data plus in-game observation. These are **estimates** and the least certain part of the model. |
| Mode structure (opponent counts, HP, fixed bosses) | Author's playthroughs |

If you find a rule that's wrong, open an issue with a screenshot or clip and it'll get fixed.

---

## Files

| File | What it is |
|---|---|
| `re7_helper_latest.py` | The whole solver: run it directly. |
| `hoffman_rule_table.json` | Hoffman decision rules and the trump catalogue (used to predict the enemy's next trump). Rules are checked top to bottom, and the first match wins. You can tweak them without touching the code. |
| `tests/test_odds.py` | Test suite for the odds maths. |

## Tests

```bash
python3 -m unittest discover tests
```

These cover:
- the round-outcome rules (including both-bust)
- draw odds
- the opponent's final-total distribution, checked against every ordering of the unseen cards for five AI profiles and eight board states (Go For targets, dead cards, already bust)
- stay vs hit, a known hidden card, Love Your Enemy, and the quick-odds command
- that every opponent's trump kit exists in the trump database

## Requirements

- Python **3.6+**, standard library only
- `hoffman_rule_table.json` in the same folder. Without it the solver still runs, but enemy-trump prediction falls back to timing rules.

## Credit

By **ThePsych** ([ThePsychDr](https://github.com/ThePsychDr)). If you build on this, please give credit.
