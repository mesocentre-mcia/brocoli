def option_is_true(option):
    option = option.lower()
    if option in ['1', 'yes', 'on', 'true']:
        return True
    elif option in ['0', 'no', 'off', 'false']:
        return False

    msg = 'invalid boolean option  value: {}'.format(option)
    raise ValueError(msg)


def option_is_false(option):
    return not option_is_true(option)

