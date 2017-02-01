# Copyright Richard Wall.
# See LICENSE for details.

"""
Yukon Solitaire.
"""

from itertools import zip_longest, chain
from random import shuffle
from string import ascii_lowercase
from unicodedata import lookup

import click
from constantly import NamedConstant, Names, ValueConstant, Values
from pyrsistent import PClass, pvector_field, field


class SUIT(Names):
    CLUBS = NamedConstant()
    DIAMONDS = NamedConstant()
    HEARTS = NamedConstant()
    SPADES = NamedConstant()


class RANK(Values):
    ACE = ValueConstant(1)
    TWO = ValueConstant(2)
    THREE = ValueConstant(3)
    FOUR = ValueConstant(4)
    FIVE = ValueConstant(5)
    SIX = ValueConstant(6)
    SEVEN = ValueConstant(7)
    EIGHT = ValueConstant(8)
    NINE = ValueConstant(9)
    TEN = ValueConstant(10)
    JACK = ValueConstant(11)
    QUEEN = ValueConstant(12)
    KING = ValueConstant(13)


class Card(PClass):
    suit = field()
    rank = field()


def deck():
    for suit in SUIT.iterconstants():
        for rank in RANK.iterconstants():
            yield Card(suit=suit, rank=rank)


def shuffled(source):
    destination = list(iter(source))
    shuffle(destination)
    return iter(destination)


class Pile(PClass):
    cards = pvector_field(Card)


class IllegalMove(Exception):
    pass


def validate_card_sequence(card1, card2):
    if card1 is None:
        if card2.rank is RANK.KING:
            return
        else:
            raise IllegalMove(
                "The first card in a pile must be a king.",
                card2
            )

    if card1.rank.value != card2.rank.value + 1:
        raise IllegalMove(
            "Card 1 must be exactly 1 rank above card2",
            card1, card2
        )


class TableauPile(Pile):
    """
    """
    hidden = pvector_field(Card)

    def append_cards(self, cards):
        if self.cards:
            card1 = self.cards[-1]
        else:
            card1 = None
        card2 = cards[0]
        validate_card_sequence(card1, card2)
        return self.transform(
            ["cards"], lambda x: x.extend(cards)
        )

    def split_at(self, index):
        if index < len(self.hidden):
            raise IndexError(
                "Index included hidden cards",
                index,
                self.hidden[index]
            )
        card_index = index - len(self.hidden)
        remaining_pile = self.transform(["cards"], self.cards[:card_index])
        if not remaining_pile.cards and remaining_pile.hidden:
            remaining_pile = TableauPile(
                hidden=remaining_pile.hidden[:-1],
                cards=[remaining_pile.hidden[-1]]
            )
        cards = self.cards[card_index:]
        return remaining_pile, cards


def validate_foundation_sequence(card1, card2):
    if card1 is None:
        if card2.rank is RANK.ACE:
            return
        else:
            raise IllegalMove(
                "The first card on a FoundationPile must be ACE.",
                card2
            )
    if card2.rank.value != card1.rank.value + 1:
        raise IllegalMove(
            "Cards must be added to the foundation pile in order.",
            card1, card2
        )


class FoundationPile(Pile):
    """
    """
    suit = field()

    def append(self, next_card):
        """
        """
        if self.cards:
            card1 = self.cards[-1]
        else:
            card1 = None
        validate_foundation_sequence(card1, next_card)

        return self.transform(
            ["cards"],
            lambda x: x.append(next_card)
        )


class Game(PClass):
    tableau = pvector_field(TableauPile)
    foundation = pvector_field(FoundationPile)


def new_game(deck):
    """
    First column has a single revealed card. Remaining columns have increasing
    numbers of hidden cards followed by five revealed.
    """
    return Game(
        tableau=[
            TableauPile(hidden=[], cards=[next(deck)])
        ] + [
            TableauPile(
                hidden=tuple(next(deck) for _ in range(i)),
                cards=tuple(next(deck) for _ in range(5))
            ) for i in range(1, 7)
        ],
        foundation=[
            FoundationPile(suit=suit, cards=[])
            for suit in SUIT.iterconstants()
        ]
    )


def card_icon(card):
    icon = lookup(
        "PLAYING CARD {} of {}".format(
            card.rank.name,
            card.suit.name
        )
    )
    fg = "white"
    if card.suit in (SUIT.DIAMONDS, SUIT.HEARTS):
        fg = "red"
    return click.style(icon, fg=fg)


def list_join(join_object, list_in):
    list_iter = iter(list_in)
    yield next(list_iter)
    for x in list_iter:
        yield join_object
        yield x


def draw_tableau(game):
    hidden_card = lookup("PLAYING CARD BACK")
    no_card = "."
    pile_iterators = tuple(
        chain(
            iter(hidden_card for card in pile.hidden),
            iter(
                card_icon(card)
                for card in pile.cards
            )
        ) for pile in game.tableau
    )
    rows = zip_longest(*pile_iterators, fillvalue=no_card)
    lines = [
        [""] + list(
            str(ascii_lowercase[i]) for i in range(len(pile_iterators))
        )
    ]
    for line_number, row in enumerate(rows, start=1):
        lines.append([str(line_number)] + list(row))
    for line in lines:
        for item in list_join("\t", line):
            click.echo(item, nl=False)
        click.echo("\n")




def draw_foundation(game):
    line = []
    for pile in game.foundation:
        if len(pile.cards) > 0:
            icon = card_icon(pile.cards[-1])
        else:
            icon = "-"
        line.append(pile.suit.name + ": " + icon)
    click.echo("\t".join(line) + "\n")


def draw_game(game):
    draw_foundation(game)
    draw_tableau(game)


class Coordinate(PClass):
    column = field(type=int)
    row = field(type=int)


class ParseError(Exception):
    pass


def parse_coordinates(coordinates):
    column = ""
    row = ""
    for c in coordinates:
        if c.isdecimal():
            row += c
        else:
            if column:
                raise ParseError("Bad coordinates", coordinates)
            column = c
    if row:
        row = int(row)-1
    else:
        row = 0
    return Coordinate(
        column=ascii_lowercase.index(column),
        row=row
    )


def move_card(game, source, destination=None):
    pile = game.tableau[source.column]
    try:
        remaining_pile, cards = pile.split_at(source.row)
    except IndexError as e:
        raise IllegalMove(
            "You can not move hidden cards.",
            e
        )
    if destination:
        game = game.transform(
            ["tableau", destination.column], lambda x: x.append_cards(cards)
        )
    else:
        if len(cards) > 1:
            raise IllegalMove(
                "You can only move a single card to a foundation pile",
                cards
            )
        card = cards[0]
        game = game.transform(
            ["foundation", lambda i: game.foundation[i].suit == card.suit],
            lambda pile: pile.append(card)
        )
    game = game.transform(
        ["tableau", source.column], remaining_pile
    )
    return game


@click.command()
def main():
    cards = shuffled(deck())
    game = new_game(cards)
    while True:
        click.clear()
        draw_game(game)
        source = click.prompt("Source?")
        source = parse_coordinates(source)
        destination = click.prompt("Destination?", default="")
        if destination:
            destination = parse_coordinates(destination)

        try:
            game = move_card(game, source, destination)
        except IllegalMove as e:
            click.echo(e)
            click.pause()
