"""Route-level orchestration for the Streamlit application."""

from collections.abc import Callable, Mapping


class ApplicationController:
    def __init__(
        self,
        game_views: Mapping[str, Callable[[], None]],
        info_views: Mapping[str, Callable[[], None]],
        default_view: Callable[[], None],
    ) -> None:
        self._game_views = game_views
        self._info_views = info_views
        self._default_view = default_view

    def render_page(self, page: str) -> None:
        view = self._game_views.get(page)
        if view is None:
            view = self._info_views.get(page, self._default_view)
        view()
