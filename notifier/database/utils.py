from importlib import import_module
from typing import Any, Callable, Tuple, Type

from notifier.database.drivers.base import BaseDatabaseDriver


def resolve_driver_from_config(driver_path: str) -> Type[BaseDatabaseDriver]:
    """For a given Python path pointing to a database driver class (e.g.
    module.package.file.DriverClass), import the module and return the
    class.
    """
    module_path, class_name = driver_path.rsplit(".", 1)
    try:
        driver_module = import_module(module_path)
    except ImportError as error:
        raise ImportError(
            f"Could not resolve driver module path {module_path} to a module"
        ) from error
    try:
        driver_class = getattr(driver_module, class_name)
    except AttributeError as error:
        raise AttributeError(
            f"Could not find driver class {class_name} in {module_path}"
        ) from error
    return driver_class


def try_cache(
    *,
    get: Callable,
    store: Callable,
    do_not_store: Any = None,
    catch: Tuple[Type[Exception], ...] = None,
) -> None:
    """Attempts to retrieve data from somewhere. If it succeeds, caches the
    data. If it fails, does nothing.

    Intended usage is for the data to be subsequently retrieved from the
    cache. This ensure that valid data is always received, even if the
    original call failed - in this case, old cached data is used instead.

    If it is necessary for the getter to succeed (e.g. for permanent
    storage of new posts), this function should not be used. It should only
    be used when failure is possible and acceptable (e.g. for temporary
    storage of user config).

    :param get: Callable that takes no argument that retrieves data, and
    may fail.

    :param store: Callable that takes the result of `get` as its only
    argument and caches the data.

    :param do_not_store: If the result of `get` is equal to this,
    it will not be stored. Defaults to None. If `get` returning None is
    desirable, set to a sentinel value.

    :param catch: Tuple of exceptions to catch. If `get` emits any other
    kind of error, it will not be caught. Defaults to catching no
    exceptions which obviously is not recommended. If an exception is
    caught, the store is not called.

    Functions intended to be used with this function typically either raise
    an error or return a no-op value, so `do_not_store` and `catch` should
    rarely be used together.
    """
    if catch is None:
        catch = tuple()
    value = do_not_store
    try:
        value = get()
    except catch as error:
        print(f"{get.__name__} failed; will use value from cache")
        print(f"Failure: {error}")
    if value != do_not_store:
        store(value)
