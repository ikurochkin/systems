import re
import sys
import argparse

import systems.models
import systems.lexer as lexer
from systems.errors import ParseException, ParseError, UnknownFlowType, ConflictingValues, DeferLineInfo


def build_stock(model, token_tuple):
    "Build stock from the lexed components."
    token, name, params_token = token_tuple
    _, params = params_token
    
    if token == lexer.TOKEN_STOCK_INFINITE:
        return model.infinite_stock(name)

    default_initial = lexer.lex_formula('0')
    initial = default_initial[:]
    maximum = systems.models.DEFAULT_MAXIMUM

    print(["build_stock", params])
    if len(params) > 0:
        initial = params[0]
    if len(params) > 1:
        maximum = params[1]

    exists = model.get_stock(name)
    if exists:
        if initial != default_initial:
            if exists.initial_lex != initial and exists.initial_lex == default_initial:
                exists.initial = initial
            else:
                raise ConflictingValues(name, exists.initial, initial)
        if maximum != systems.models.DEFAULT_MAXIMUM:
            if exists.maximum != maximum and exists.maximum == systems.models.DEFAULT_MAXIMUM:
                exists.maximum = maximum
            else:
                raise ConflictingValues(name, exists.maximum, maximum)
        return exists

    return model.stock(name, initial, maximum)


def parse_stock(model, txt):
    "Parse stock from raw text. Used primarily for testing or iterative parsing."
    return build_stock(model, lexer.lex_stock(txt))


def build_flow(model, src, dest, token):
    _, class_str, params_token = token
    _, params = params_token

    rate_class = None
    class_str = class_str.lower()
    if class_str == "leak":
        rate_class = systems.models.Leak
    elif class_str == "conversion":
        rate_class = systems.models.Conversion
    elif class_str == "rate":
        rate_class = systems.models.Rate
    elif class_str == '':
        print(["oook", params[0][1]])
        if len(params[0][1]) == 2 and params[0][1][0] == lexer.TOKEN_DECIMAL:
            rate_class = systems.models.Conversion
        else:
            rate_class = systems.models.Rate
    else:
        raise UnknownFlowType(class_str)

    rate = rate_class(*params)
    print(["RATE", rate_class, token])
    return model.flow(src, dest, rate)


def parse_flow(model, src, dest, txt):
    "Parse flow from raw text. Used primarily for testing or iterative parsing."    
    return build_flow(model, src, dest, lexer.lex_flow(txt))


def parse(txt):
    m = systems.models.Model("Parsed")
    stocks = []
    by_name = {}
    flows = []

    tokens = lexer.lex(txt)
    for _, n, line in tokens:
        first_stock = None
        second_stock = None

        try:
            for token in line:
                if token[0] in (lexer.TOKEN_STOCK, lexer.TOKEN_STOCK_INFINITE):
                    if first_stock is None:
                        first_stock = build_stock(m, token)
                    elif second_stock is None:
                        second_stock = build_stock(m, token)
                elif token[0] == lexer.TOKEN_FLOW:
                    build_flow(m, first_stock, second_stock, token)
        except DeferLineInfo as dli:
            dli.line = line
            dli.line_number = n
            raise dli
        except Exception as e:
            raise ParseError(line, n, e)

    return m


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        '-r',
        '--rounds',
        type=int,
        help="number of rounds to run evaluation",
        default=10)
    p.add_argument('--csv', action='store_true', default=False)
    args = p.parse_args()

    txt = sys.stdin.read()

    try:
        model = parse(txt)
    except ParseException as pe:
        print(pe)
        return

    results = model.run(rounds=args.rounds)
    kwargs = {}
    if args.csv:
        kwargs['sep'] = ','
        kwargs['pad'] = False
    print(model.render(results, **kwargs))


if __name__ == "__main__":
    main()
