import inspect


def wolflistener(name=None, priority=0):
    """A decorator that marks a function as a listener.

    This is the werewolf.Game equivalent of :meth:`.Cog.listener`.

    Parameters
    ------------
    name: :class:`str`
        The name of the event being listened to. If not provided, it
        defaults to the function's name.
    priority: :class:`int`
        The priority of the listener.
        Priority guide as follows:
        _at_night_start
        0. No Action
        1. Detain actions (Jailer/Kidnapper)
        2. Group discussions and choose targets

        _at_night_end
        0. No Action
        1. Self actions (Veteran)
        2. Target switching and role blocks (bus driver, witch, escort)
        3. Protection / Preempt actions (bodyguard/framer)
        4. Non-disruptive actions (seer/silencer)
        5. Disruptive actions (Killing)
        6. Role altering actions (Cult / Mason / Shifter)

    Raises
    --------
    TypeError
        The function is not a coroutine function or a string was not passed as
        the name.
    """

    if name is not None and not isinstance(name, str):
        raise TypeError(
            "Game.listener expected str but received {0.__class__.__name__!r} instead.".format(
                name
            )
        )

    def decorator(func):
        actual = func
        if isinstance(actual, staticmethod):
            actual = actual.__func__
        if not inspect.iscoroutinefunction(actual):
            raise TypeError("Listener function must be a coroutine function.")
        actual.__wolf_listener__ = priority
        to_assign = name or actual.__name__
        try:
            actual.__wolf_listener_names__.append((priority, to_assign))
        except AttributeError:
            actual.__wolf_listener_names__ = [(priority, to_assign)]
        # we have to return `func` instead of `actual` because
        # we need the type to be `staticmethod` for the metaclass
        # to pick it up but the metaclass unfurls the function and
        # thus the assignments need to be on the actual function
        return func

    return decorator


class WolfListenerMeta(type):
    def __new__(mcs, *args, **kwargs):
        name, bases, attrs = args

        listeners = {}
        need_at_msg = "Listeners must start with at_ (in method {0.__name__}.{1})"

        new_cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        for base in reversed(new_cls.__mro__):
            for elem, value in base.__dict__.items():
                if elem in listeners:
                    del listeners[elem]

                is_static_method = isinstance(value, staticmethod)
                if is_static_method:
                    value = value.__func__
                if inspect.iscoroutinefunction(value):
                    try:
                        is_listener = getattr(value, "__wolf_listener__")
                    except AttributeError:
                        continue
                    else:
                        # if not elem.startswith("at_"):
                        #     raise TypeError(need_at_msg.format(base, elem))
                        listeners[elem] = value

        listeners_as_list = []
        for listener in listeners.values():
            for priority, listener_name in listener.__wolf_listener_names__:
                # I use __name__ instead of just storing the value so I can inject
                # the self attribute when the time comes to add them to the bot
                listeners_as_list.append((priority, listener_name, listener.__name__))

        new_cls.__wolf_listeners__ = listeners_as_list
        return new_cls


class WolfListener(metaclass=WolfListenerMeta):
    def __init__(self, game):
        for priority, name, method_name in self.__wolf_listeners__:
            game.add_ww_listener(getattr(self, method_name), priority, name)
