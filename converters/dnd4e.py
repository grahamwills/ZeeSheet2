from __future__ import annotations

import json
import re
from collections import defaultdict, namedtuple
from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Dict, List, NamedTuple, Optional

import xmltodict


def style_definitions():
    return dedent("""
        .. styles::
            default
              font-family:'Montserrat' font-size:9
            default-block
              border:none effect:none margin:8 text-align:left background:#cdf
            skills-block
              text-align:auto background:#cfd
            default-section
              margin:'0 -8'
            attributes-red:
              background:#b00 padding:'4 2'
            attributes-blue:
              background:#00b padding:'4 2'
            attributes-title:
              color:white padding:'10 0.1'
            power-block
              margin:8 effect:rounded
            default-title
              font-size:11
            
            title
             text-color:#b00 font-family:Almendra font-size:40 background:none
            blue
             parent:power-block background:#eef
            black
             parent:power-block background:#eee
            green
             parent:power-block background:#efe
            red
             parent:power-block background:#fdd
            orange
             parent:power-block background:#efb261
    """)


Weapon = namedtuple('Weapon', 'name bonus damage attack_stat defense conditions')

USAGE_TYPE = {
    'At-Will': (1, 'green'),
    'Encounter': (2, 'red'),
    'Daily': (3, 'black'),
    'Item': (4, 'orange')
}

ACTION_TYPE = {
    'Standard': (0, '❖ ', 'Std'),
    'Move': (1, '→', 'Move'),
    'Movement': (1, '→', 'Move'),
    'Minor': (2, '☉ ', 'Minor'),
    'Free': (3, '∅ ', 'Free'),
    'No': (4, '∅ ', 'No'),
    'Opportunity': (5, '☇', 'Opp'),
    'Immediate Interrupt': (6, '☇', 'Int'),
    'Immediate Reaction': (7, '☇', 'React'),
    '': (8, '', '--')
}


def read_rules_elements() -> Dict:
    d = xml_file_to_dict('converters/dnd4e_combined.xml')
    top = d['D20Rules']['RulesElement']
    result = dict((p['@internal-id'], p) for p in top)
    print("Read %d rules" % len(result))
    return result


def _find(txt: str, rule: Dict) -> Optional[str]:
    for item in rule['specific']:
        if item['@name'] == txt:
            return item.get('#text', None)
    return None


def _find_extras(rule: Dict) -> List[(str, str)]:
    pair = []
    prefix = ''
    for item in rule['specific']:
        if item['@name'] == 'Augment':
            prefix = '[Augment ' + item['#text'] + '] '
        elif item['@name'].startswith(' '):
            pair.append((prefix + item['@name'].strip(), item['#text'].strip()))
        else:
            prefix = ''
    return pair


def _combine(target, range):
    if target:
        target = target.split('\n')[0]
    if range:
        range = range.split('\n')[0]

    if not target and not range:
        return None
    if target and not range:
        return target
    if not target and range:
        return range

    if range == 'Melee Weapon':
        return "%s (melee)" % target
    if range.startswith('Ranged'):
        return "%s within %s" % (target, range[7:].strip())
    if 'burst' in target:
        return target.replace('burst', range.lower())


def _rollify(txt, mult):
    """Find dice in the text and replace them"""
    match = re.match("(.*)([1-9]d[0-9][0-9]?[+-]*[0-9]+)(.*)", txt)
    if match:
        roll = " ".join(['[[' + match.group(2) + ']]'] * mult)
        return _rollify(match.group(1), mult) + roll + _rollify(match.group(3), mult)
    else:
        return txt


def display(t: tuple, bold_item: int = 0) -> str:
    result = None
    for i, v in enumerate(t):
        if v:
            if i == bold_item:
                v = '**' + v + '**'
            if i == 0:
                result = v
            elif i == 1:
                result = result + ": " + v
            else:
                result = result + ' • ' + v
    return result


class Power(NamedTuple):
    name: str
    usage: str
    action: str
    weapons: List[Weapon]

    def is_skippable(self):
        return self.name in {'Bull Rush Attack', 'Opportunity Attack', 'Grab Attack'}

    def to_rst(self, rule: Dict, replacements: List[(str, str)]) -> str:
        components = self.to_components(replacements, rule)
        return self.components_to_rst(components)

    def to_roll20(self, rule: Dict, replacements: List[(str, str)]) -> str:
        components = self.to_components(replacements, rule)
        return self.components_to_roll20(components)

    def to_components(self, replacements, rule):
        components = defaultdict(lambda: '')
        components['source'] = rule['@source'].replace("Player's Handbook ", 'PHB').replace(" Magazine", '')
        disp = _find('Display', rule)
        if disp:
            components['class'] = disp.replace(' Attack', '').replace(' Feature', '').replace(' Racial', '')
        attack_type = _find('Attack Type', rule)
        target = _find('Target', rule)
        keys = _find('Keywords', rule)
        if keys:
            components['keywords'] = keys.replace(',', ' • ')
        extras = _find_extras(rule)
        atk_target = _combine(target, attack_type)
        if atk_target:
            atk_target = atk_target.replace("One, two, or three", "Up to three")
        if self.weapons:
            wpn = self.weapons[0]
            components['wpn_bonus'] = wpn.bonus
            components['wpn_defense'] = wpn.defense
            if atk_target:
                components['atk_target'] = atk_target
            if wpn.conditions:
                components['conditions'] = wpn.conditions
        elif atk_target:
            components['atk_target'] = atk_target
        lines_main = []
        for key in "Requirement Trigger Hit Miss Effect".split():
            txt = _find(key, rule)
            if txt:
                txt = str(txt)
                for k, v in replacements:
                    txt = txt.replace(k, v)
                txt = self.further_tidying(txt)
                lines_main.append((key, txt.split('\n')[0].replace(' + ', '+')))
        lines_main += extras

        if 'Flavor' in rule:
            components['flavor'] = rule['Flavor']
        components['action_icon'] = ACTION_TYPE[self.action][1]
        components['usage'] = self.usage
        components['name'] = self.name
        components['action_type'] = self.action
        components['action_type_short'] = ACTION_TYPE[self.action][2]
        components['main_as_list'] = lines_main
        return components

    def components_to_rst(self, components):
        if len(components['name']) + len(components['action_type']) > 28:
            act_type = components['action_type_short']
        else:
            act_type = components['action_type']
        box = '' if components['usage'] == 'At-Will' else ' [ ]'
        line_title = (components['action_icon'], components['name'], act_type, box)
        color = USAGE_TYPE[components['usage']][1]
        lines = [
            ".. block:: style=%s\n" % color,
            "%s **%s** | %s%s\n" % line_title
        ]
        if 'wpn_bonus' in components and 'atk_target' in components:
            lines.append("- **+%s** vs. **%s** | %s" % (
                components['wpn_bonus'], components['wpn_defense'], components['atk_target']))
        elif 'wpn_bonus' in components:
            lines.append("- **+%s** vs. **%s**" % (components['wpn_bonus'], components['wpn_defense']))
        elif 'atk_target' in components and components['atk_target'] != 'Personal':
            lines.append("- | %s" % components['atk_target'])
        for line in components['main_as_list']:
            lines.append("- **%s**: %s" % line)
        if 'conditions' in components:
            lines.append("- %s" % components['conditions'])
        if components['flavor']:
            lines.append("- *%s*" % components['flavor'])

        if 'keywords' in components:
            lines.append(
                "- %s • %s • %s" % (
                    components['keywords'], components.get('class', ''), components['source']))
        else:
            lines.append("- %s • %s" % (
                components.get('class', ''), components['source']))
        result = '\n'.join(line for line in lines if line)
        return result

    def components_to_roll20(self, components: Dict):
        lines = []
        lines.append("%16s: %s" % ('Power Name', components['name']))
        lines.append("%16s: %s" % ('Power Action', components['action_type']))
        lines.append("%16s: %s" % ('Power Range', components['atk_target']))
        lines.append("%16s: %s" % ('Power Usage', components['usage']))
        lines.append("macro:")

        color = components['usage'].lower().replace('-', '')

        macro = "&{template:dnd4epower} {{%s=yes}} {{name=%s}} {{target=%s}}" % (
            color,
            components['name'],
            components['atk_target'],
        )

        # Count if there are more rolls we need to add
        attacks = 1
        damages = 1

        for k, v in components['main_as_list']:
            if k == 'Effect' and 'one more time' in v:
                attacks = 2
                damages = 2

        if 'two' in components['atk_target'].lower():
            attacks = 2
        if 'three' in components['atk_target'].lower():
            attacks = 3
        if 'each' in components['atk_target'].lower():
            attacks = 4

        if 'wpn_bonus' in components:
            attack_list = " ".join(["[[1d20+%s]]" % components['wpn_bonus']] * attacks)
            macro += "{{attack=%s vs. %s}}" % (attack_list, components['wpn_defense'])

        for k, v in components['main_as_list']:
            if k == 'Hit':
                k = 'Damage'
            macro += " {{%s=%s}}" % (k.lower(), _rollify(v, damages))

        if 'conditions' in components:
            macro += " {{special=%s}}" % components['conditions']
        if 'keywords' in components:
            macro += " {{keywords=%s}}" % components['keywords']
        if 'flavor' in components:
            macro += " {{emote=%s}}" % components['flavor']

        lines.append(macro)
        lines.append('\n')

        return "\n".join(lines)

    def order(self):
        return str(USAGE_TYPE[self.usage][0] * 10 + ACTION_TYPE[self.action][0]) + '_' + self.name

    def further_tidying(self, txt):
        """ Make common phrases cleaner to read"""
        match = re.match("(.* gain )([a-z ]+) equal to ([0-9+\\- ]+)\\.", txt)
        if match:
            txt = match.group(1) + ' ' + self.eval(match.group(3)) + ' ' + match.group(2)
        match = re.match("(.* take[s]+ )([a-z ]+) equal to ([0-9+\\- ]+)\\.", txt)
        if match:
            txt = match.group(1) + ' ' + self.eval(match.group(3)) + ' ' + match.group(2)
        return txt

    def eval(self, txt):
        return str(sum(int(s.strip()) for s in txt.split('+')))


def _to_weapon(item) -> Weapon:
    return Weapon(
        item['@name'],
        item['AttackBonus'],
        item['Damage'],
        item['AttackStat'],
        item['Defense'],
        item.get('Conditions', '')
    )


def _to_power(item) -> Power:
    usage = '????'
    action = '????'
    for s in item['specific']:
        if s['@name'] == 'Power Usage':
            usage = s['#text'].replace(' (Special)', '')
        if s['@name'] == 'Action Type':
            action = s['#text'].replace(' Action', '')

    if 'Weapon' in item:
        wlist = item['Weapon']
        try:
            weapons = [_to_weapon(sub) for sub in wlist]
        except:
            # Just one item
            weapons = [_to_weapon(wlist)]
    else:
        weapons = []

    return Power(
        name=item['@name'],
        action=action,
        usage=usage,
        weapons=weapons
    )


def _to_item(item) -> Power:
    try:
        item = item[-1]
    except:
        pass

    return Power(
        name=item['@name'],
        action='',
        usage='Item',
        weapons=[]
    )


def _pair(base, name):
    return name, (base[name])


def _titled(name: str) -> str:
    return name + '\n' + '=' * len(name) + '\n'


def _block(items: []) -> Dict:
    d = dict()

    for item in items:
        value = int(item['@value'])
        alias = item['alias']
        try:
            name = alias['@name']
        except:
            name = alias[0]['@name']
        name = name.replace(' Defense', '')
        d[name] = value

    return d


def _to_rule_tuple(t):
    try:
        descr = t['specific']['#text']
    except:
        descr = None

    if not descr:
        try:
            descr = _find('Flavor', t) or _find('Short Description', t)
        except:
            descr = None
    return t['@name'], re.sub('[\n\t ]{2,}', ' ', descr or '')


def _format_tuple_3_as_line(p):
    if len(p) < 2 or not p[2]:
        return "- %s: **%s**" % (p[0], p[1])
    else:
        return "- %s: **%s** | %s" % p


class DnD4E:
    rule_elements: Dict
    character: Dict
    level: int
    half_level: int
    stats: Dict

    def __init__(self, base: Dict, rule_elements, file):
        self.directory = Path(file).parent
        self.rule_elements = rule_elements
        base = base['D20Character']
        self.character = base['CharacterSheet']
        self.level = int(base['CharacterSheet']['Details']['Level'])
        self.half_level = self.level // 2
        self.stats = _block(base['CharacterSheet']['StatBlock']['Stat'])

    def val(self, s) -> int:
        return self.stats[s]

    def print(self):
        print(json.dumps(self.character, indent=2))

    def rule_tuple(self, name):
        rule = self.rule(name)
        return name, rule[0], rule[1]

    def rule_tuple2(self, name):
        value = self.rule(name)
        assert not value[1]
        return name, value[0]

    def rule(self, rule_type: str) -> (str, str):
        targets = self.rules(rule_type)
        if not targets:
            return None, None
        assert len(targets) == 1
        return targets[0]

    def rules(self, rule_type: str) -> List[(str, str)]:
        """ Returns a list of matching items, as tuples of name, description"""
        items = self.character['RulesElementTally']['RulesElement']
        return [_to_rule_tuple(t) for t in items if t['@type'] == rule_type]

    def character_title(self) -> str:
        name = self.character['Details']['name']
        return name

    def character_details(self) -> str:

        profs = [p[0] for p in self.rules('Proficiency')
                 if p[0].startswith('Armor') or p[0].startswith('Implement') or not '(' in p[0]]

        base = self.character['Details']
        pairs = [
                    self.rule_tuple2('Gender'),
                    self.rule_tuple2('Alignment'),
                    self.rule_tuple2('Background'),
                    self.rule_tuple2('Theme'),
                    self.rule_tuple2('Deity'),
                    ('Domain', self.join_names('Domain', join=', ')),
                    self.rule_tuple2('Vision'),
                    self.rule_tuple2('Size'),
                    ('Languages', self.join_names('Language')),
                    ('Passive Perception', self.stats['Passive Perception']),
                    ('Passive Insight', self.stats['Passive Insight']),

                ] + [_pair(base, key) for key in "Age Height Weight".split()]

        result = ''
        first = True
        for p in pairs:
            if p[1]:
                if first:
                    result += "\n- %20s: **%s**" % p
                    first = False
                else:
                    result += " | %20s: **%s**" % p
                    first = True

        result += '\n - Proficiencies: *' + " • ".join(p.replace('Proficiency ', '') for p in profs) + '*'
        return result

    def add_detailed_descriptions(self, tuples, target, target_as_name):
        simple = self.rules(target)
        for c in simple:
            name = c[0]
            rule = self.rule_elements[c[1]]
            descr = _find('Short Description', rule)
            tuples.append((target_as_name, name, descr))

    def stat_block(self):
        stats = "Strength Constitution Dexterity Intelligence Wisdom Charisma".split()
        tuples = [(name, "**%d**" % self.val(name), self.stat_bonus(name) + self.half_level) for name in stats]
        return 'Ability Scores\n\n' + "\n".join(["- %-12s | %6s | *+%s*" % p for p in tuples])

    def skills(self):
        skills = []
        for item in self.character['StatBlock']['Stat']:
            value = int(item['@value'])
            try:
                name = item['alias'][0]['@name']
            except:
                name = item['alias']['@name']

            if not name + ' Trained' in self.stats:
                continue

            trained = self.stats[name + ' Trained'] > 0

            skills.append((value, name, trained))
        skills.sort(key=lambda x: x[1])
        skills = [(value, '**%s**' % name if trained else name) for value, name, trained in skills]
        return 'Skills\n\n' + "\n".join(["- %16s | **%d**" % (s[1], s[0]) for s in skills])

    def class_features(self):

        tuples: List[(str, str, str)] = []

        # Check for hybrid classes
        hybrids = self.rules('Hybrid Class')
        if hybrids:
            for h in hybrids:
                tuples.append(('Class', h[0], h[1]))
        elif self.rules('CountsAsClass'):
            self.add_detailed_descriptions(tuples, 'CountsAsClass', 'Class')
        else:
            v1, v2 = self.rule('Class')
            tuples.append(('Class', v1, v2))

        name = '/'.join(t[1] for t in tuples)
        rules = self.rules('Class Feature')
        return f'Class: {name}\n\n' + "\n".join(["- " + display(s) for s in tuples + rules])

    def racial_features(self):
        tuples = self.rules('Race')
        name = '/'.join(r[0] for r in tuples)
        rules = self.rules('Racial Trait')
        rules = [r for r in rules if r[1] != '@']
        return f'Race: {name}\n\n' + "\n".join(["- " + display(s) for s in tuples + rules])

    def feats(self):
        rules = self.rules('Feat')
        rules.sort(key=lambda x: ('A' if x[1] else 'B') + x[0])
        return 'Feats\n\n' + "\n".join(["- " + display(s) for s in rules])

    def defenses(self, names):
        stats = names.split()
        tuples = [(name, "**%d**" % self.val(name)) for name in stats]
        return 'Combat\n\n' + "\n".join(["- %-12s | %6s" % p for p in tuples])

    def hits(self):
        first_line = ['Action Points: [ ][ ][ ]']
        for key, name in (
                ('Healing Surges', 'Surges'), ('Power Points', 'Power Points'), ('Death Saves Count', 'Death Saves')
        ):
            value = int(self.stats.get(key, 0))
            if value:
                first_line.append(name + ': ' + '[ ]' * value)

        save_bonus = int(self.stats.get('Death Saving Throws', 0))
        if save_bonus:
            first_line[-1] = first_line[-1] + f"[at +{save_bonus}]"

        hits = self.val('Hit Points')

        second_line = "- Hits: **%d** [[---------]]  Bloodied: **%d**\n" % (hits, hits // 2)

        return '- ' + ' | '.join(first_line) + '\n' + second_line \
               + "- [[---------------------------]]\n" \
               + "- [[---------------------------]]\n"

    def power_cards(self) -> List[str]:

        power_mapping = self.power_mappings()

        powers = [_to_power(s) for s in self.character['PowerStats']['Power']]
        powers = [p for p in powers if not p.is_skippable()]
        powers.sort(key=lambda p: p.order())

        items = [p.to_rst(power_mapping.get(p.name), self.make_replacements(p)) for p in powers]
        file = self.directory.joinpath('_powers.rst')
        if file.exists():
            items.append(file.read_text())

        items += [self.item_to_rst(item) for item in self.item_list()]
        file = self.directory.joinpath('_items.rst')
        if file.exists():
            items.append(file.read_text())

        return items

    def to_rst(self) -> str:

        front_page = [
            ".. sheet:: quality=high image-mode=stretch width=8in height=11.5in",
            ".. section:: columns=2",
            ".. block::   title-style=title",
            self.character_title(),
            ".. block::   title-style=default-title",
            self.character_details(),
            ".. block::   method=attributes style=attributes-red  title-style=attributes-title",
            self.defenses("AC Fortitude Reflex Will Initiative Speed"),

            ".. section:: columns=1",
            self.hits(),

            ".. section:: columns=2",
            ".. block::   method=attributes style=attributes-blue title-style=attributes-title",

            self.stat_block(),

            ".. block::   method=table style=skills-block",
            self.skills(),
            ".. block::   method=table style=default-block",
            self.class_features(),
            self.racial_features(),
            self.feats(),

            ".. section:: columns=3",
            ".. block:: style=default",

        ]
        return "\n\n\n".join(x for x in front_page if x) \
               + '\n\n\n' \
               + "\n\n\n".join(self.power_cards()) \
               + '\n\n\n' + style_definitions()

    def _stat_of(self, base) -> (str, int, int):
        try:
            value = int(base['@value'])
            alias = base['alias']
            name = alias[0]['@name']
            bonus = (value - 10) // 2 + self.half_level
            return name, '**' + str(value) + '**', bonus
        except:
            return None, None, None

    def join_names(self, rule_type: str, join: str = ' • '):
        return join.join(p[0] for p in self.rules(rule_type))

    def power_mappings(self) -> Dict:
        items = self.character['RulesElementTally']['RulesElement']
        return dict([(t['@name'], self.rule_elements[t['@internal-id']]) for t in items if t['@type'] == 'Power'])

    def item_list(self) -> [List[str]]:
        items = self.character['LootTally']['loot']
        result = []
        for item in items:
            if item['@count'] == '0':
                continue
            element = item['RulesElement']
            try:
                result.append([e['@internal-id'] for e in element])
            except:
                result.append([element['@internal-id']])
        return result

    def divider(self) -> str:
        return '-' * 40

    def make_replacements(self, p: Power) -> List[(str, str)]:
        """ replace common text in hits, misses and effects"""

        reps = []

        damage_bonus = 0

        if p.weapons and p.weapons[0].damage:
            damage = p.weapons[0].damage
            attack_stat = p.weapons[0].attack_stat
            count = int(damage[0])
            full_damage = damage[1:]
            split = full_damage.split('+')
            dice = split[0]
            if len(split) > 1:
                bonus = "+" + split[1]
                damage_bonus = int(bonus[1:]) - self.stat_bonus(attack_stat)
            else:
                bonus = ''

            for i in range(1, 10):
                reps.append(("%d[W] + %s modifier" % (i, attack_stat), "%d%s%s" % (i * count, dice, bonus)))
                reps.append(("%d[W]" % i, "%d%s%s" % (i * count, dice, bonus)))

        for stat in "Strength Constitution Dexterity Intelligence Wisdom Charisma".split():
            value = str(self.stat_bonus(stat) + damage_bonus)
            reps.append(("your %s modifier" % stat, value))
            reps.append(("%s modifier" % stat, value))

        return reps

    def stat_bonus(self, attack_stat):
        return (self.val(attack_stat) - 10) // 2

    def item_to_rst(self, ids: List[str]):

        # Merge rules for each ID
        rule = dict()
        for id in ids:
            rule.update(self.rule_elements[id])

        name = rule['@name'].replace(' (heroic tier)', '').strip()
        item_type = _find('Magic Item Type', rule)
        slot = _find('Item Slot', rule)
        line_flavor = rule.get('Flavor', rule.get('#text', None))
        price = _find('Gold', rule)
        rarity = _find('Rarity', rule)

        # Power needs special care, example:
        #   Power (Daily): Free Action. Trigger: You miss with a melee attack using this staff. Effect:
        #   Reroll the attack roll and use the second result, even if it is lower than the first.
        power = _find('Power', rule)
        if power:
            rparen = power.index('):')
            usage = power[7:rparen].strip()
            txt = power[rparen + 2:].strip()
            dot = txt.index('.')
            action = txt[:dot].strip().replace(' Action', '')
            power = (action, txt[dot + 1:])
            box = '' if usage == 'At-Will' else ' [ ]'
            info = ACTION_TYPE[action]
            line_title = "**%s** | %s%s" % (name, info[2], box)
        else:
            line_title = "**%s** | %s" % (name, slot or item_type)

        if '@source' in rule:
            source = rule['@source'].replace("Player's Handbook", 'PHB').replace(" Magazine", '') \
                .replace("Mordenkainen's Magnificent Emporium", 'Mordenkainen')
        else:
            source = ''

        line_info = (rarity, price, slot or item_type)

        lines_main = []
        for key in "Enhancement Property Critical".split():
            txt = _find(key, rule)
            if txt:
                lines_main.append((key, txt))
        if power:
            lines_main.append(power)

        color = USAGE_TYPE['Item'][1]

        lines = [
            ".. block:: style=%s\n\n" % color,
            line_title,
            "\n- %s • %sgp | %s" % line_info,
        ]

        for line in lines_main:
            lines.append("- **%s**: %s" % line)
        lines.append("- *%s*" % line_flavor)

        if source:
            lines.append("- | %s" % source)

        return '\n'.join(line for line in lines if line)

    def to_roll20(self):
        power_mapping = self.power_mappings()

        powers = [_to_power(s) for s in self.character['PowerStats']['Power']]
        powers.sort(key=lambda p: p.order())

        out = StringIO()
        for p in powers:
            p.to_components(self.make_replacements(p), power_mapping.get(p.name))
            out.write(p.to_roll20(power_mapping.get(p.name), self.make_replacements(p)))
            out.write('\n')

        return out.getvalue()


def read_dnd4e(f, rules: Dict) -> DnD4E:
    dict = xml_file_to_dict(f)
    return DnD4E(dict, rules, f)


def xml_file_to_dict(filename):
    with open(filename, 'r') as f:
        data = f.read()
    dict = xmltodict.parse(data, process_namespaces=True, )
    return dict


def convert_dnd4e(file: Path) -> Path:
    rules = read_rules_elements()
    dnd = read_dnd4e(file, rules)
    out = dnd.to_rst()
    out_file = file.parent.joinpath(file.stem + '.rst')

    with open(out_file, 'w') as file:
        file.write(out)
    return out_file


if __name__ == '__main__':
    rules = read_rules_elements()

    dnd = read_dnd4e('../data/characters/Grumph/grumph-6.dnd4e', rules)

    out = dnd.to_roll20()

    with open('../data/characters/Grumph/grumph_roll20.txt', 'w') as file:
        file.write(out)
