import dataclasses
import inspect
from contextvars import ContextVar
from dataclasses import _MISSING_TYPE
from typing import Callable, Coroutine, List, cast

import kayaku
import typing_extensions
from kayaku.schema_gen import ConfigModel
from rich.markdown import Markdown
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.events import Key
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Static
from typing_extensions import Self

__import__("model")

CURRENT_SCREEN = ContextVar("CURRENT_SCREEN", default="")
INSTALLED_SCREENS = ContextVar("INSTALLED_SCREENS", default=[])
TUI_APP = ContextVar("TUI_APP")

_WELCOME_MD = """
## Eric 配置编辑器

暂不完善，仅供测试

目前 TUI 仅支持编辑 Eric 的库配置。
由于未加载模块，暂不支持编辑模块配置。
"""

_NO_MODELS_MD = """
## 错误

未找到可用的 Kayaku ConfigModel
"""


def merge_classes(*classes: str) -> str:
    cls = []
    for c in classes:
        if c and isinstance(c, str):
            cls.extend(c.split())
    cls = [{c for c in cls if c}]
    return " ".join(cls)


class MessageBox(Container):
    def __init__(
        self,
        static: Static,
        button: Button | None = None,
        button_callback: Callable[[], None | Coroutine] = None,
        classes: str = "",
    ):
        super().__init__(classes=classes)
        self._static = static
        self._button = button
        self._button_callback = button_callback

    def compose(self) -> ComposeResult:
        yield self._static
        if self._button:
            yield self._button

    async def on_button_pressed(self, event: Button.Pressed):
        if not self._button:
            return
        if event.button.id == self._button.id and self._button_callback:
            obj = self._button_callback()
            while inspect.isawaitable(obj):
                obj = await obj


class FallbackScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Center(
            MessageBox(
                Static(Markdown(_NO_MODELS_MD, justify="center")),
                Button("退出", id="fallback_exit", variant="error"),
                self.app.action_quit,
                classes="fallback",
            )
        )
        yield Footer()


class InputPair(Container):
    pass


class InputField(Container):
    data: str

    def __init__(
        self, classes: str, label: str, placeholder: str, description: str | Text = None
    ):
        super().__init__(classes=classes)
        self._field_label = label
        self._field_placeholder = placeholder
        self._field_description = description

    def compose(self) -> ComposeResult:
        container = [
            InputPair(
                Static(self._field_label, classes="label"),
                Input(placeholder=self._field_placeholder),
            )
        ]
        if self._field_description:
            container.append(Static(self._field_description, classes="description"))
        yield from container

    def on_input_changed(self, message: Input.Changed) -> None:
        self.data = message.value


class FrozenInput(Static):
    pass


class MutableInputPair(Container):
    pass


class MutableInputField(Container):
    data: list[str]
    _widgets: reactive[dict[str, Widget]] = reactive({}, layout=True)
    _input: str

    @property
    def button_id_prefix(self):
        return f"{self._field_classes}"

    def __init__(
        self, classes: str, label: str, placeholder: str, description: str | Text = None
    ):
        super().__init__(classes=classes)
        self._field_classes = classes
        self._field_label = label
        self._field_placeholder = placeholder
        self._field_description = description
        self.data = []
        self._input = ""

    def compose(self) -> ComposeResult:
        container = [
            MutableInputPair(
                Static(self._field_label, classes="label"),
                Input(
                    placeholder=self._field_placeholder,
                    classes=f"{self.button_id_prefix}_input",
                ),
                Button("+", id=f"{self.button_id_prefix}_add", variant="primary"),
            )
        ]
        if self._field_description:
            container.append(Static(self._field_description, classes="description"))
        yield from container

    def on_input_changed(self, message: Input.Changed) -> None:
        self._input = message.value

    def on_button_pressed(self, event: Button.Pressed):
        if not event.button.id or not event.button.id.startswith(self.button_id_prefix):
            return
        if event.button.id.startswith(f"{self.button_id_prefix}_remove"):
            index = event.button.id.split("_")[-1]
            if index in self._widgets:
                self._widgets[index].remove()
                del self._widgets[index]
            return
        if not self._input:
            self.screen.mount(Notification("输入不能为空"))
            return
        index = len(self.data) + 1
        self.mount(
            pair := MutableInputPair(
                Static("", classes="label"),
                FrozenInput(self._input),
                Button(
                    "-", id=f"{self.button_id_prefix}_remove_{index}", variant="error"
                ),
                classes=f"{self._field_classes}_data_{index} _margin-top",
            )
        )
        self.data.append(self._input)
        self._widgets[str(index)] = pair
        self._input = ""
        box = self.query_one(f".{self.button_id_prefix}_input")
        box.value = ""
        return


class ScreenLink(Static):
    def __init__(self, label: str, screen: str) -> None:
        super().__init__(label)
        self.reveal = screen

    def on_click(self) -> None:
        self.app.push_screen(self.reveal)


class KayakuScreen(Screen):
    components: tuple[Widget, ...]

    def __init__(self, model: ConfigModel, *components: Widget):
        super().__init__()
        self._model = model
        self.components = components

    def compose(self) -> ComposeResult:
        yield from self.components

    @staticmethod
    def is_required_field(field: dataclasses.Field) -> bool:
        return isinstance(field.default, _MISSING_TYPE) and isinstance(
            field.default_factory, _MISSING_TYPE
        )

    @staticmethod
    def assemble_description(required: bool, docs: str, hint: str) -> Text:
        if not required and not docs:
            return Text(hint, style="bold green")
        require_prefix = ("*必填 ", "bold red") if required else ""
        return Text.assemble(
            require_prefix, docs, "\n\n", "@type: ", (hint, "bold green")
        )

    @classmethod
    def from_model(cls, model: type) -> Self:
        model = cast(ConfigModel, model)
        components: list[Widget] = [
            ContainerTitle(Static(model.__name__, classes="kayaku-model-name"))
        ]
        type_hints = typing_extensions.get_type_hints(model, include_extras=True)
        for field in dataclasses.fields(model):
            typ = type_hints[field.name]
            hint = (
                f"{typ!r}"
                if (typ_origin := typing_extensions.get_origin(typ))
                else f"{typ.__name__}"
            )
            docs = field.metadata.get("description", "")
            desc = cls.assemble_description(cls.is_required_field(field), docs, hint)
            if field.default == "":
                default = "<未设置>"
            elif isinstance(field.default, _MISSING_TYPE):
                default = ""
            else:
                default = field.default
            input_field = MutableInputField if typ_origin == list else InputField
            components.append(
                input_field(model.__name__, f"{field.name}", str(default), desc)
            )
        return cls(model, Header(), Body(quick_access, *components), Footer())


class Body(Container):
    pass


class Center(Container):
    pass


class ContainerTitle(Container):
    pass


class QuickAccess(Container):
    def reg_screen(self, screen: str):
        self.mount(ScreenLink(screen, screen))


class Notification(Static):
    def on_mount(self) -> None:
        self.set_timer(3, self.remove)

    def on_click(self) -> None:
        self.remove()


quick_access = QuickAccess()


class EricTUI(App):
    CSS_PATH = "../textual.css"
    TITLE = "Eric 配置"
    BINDINGS = [
        Binding("ctrl+c", "quit", "退出", priority=True),
        ("s", "save", "保存"),
    ]

    def compose(self) -> ComposeResult:
        mount_screens(self)
        yield Header()
        yield Center(
            MessageBox(
                Static(Markdown(_WELCOME_MD, justify="center")),
                Button("开始", id="welcome_start", variant="success"),
                self.app.action_next_screen,
                classes="welcome",
            )
        )
        yield Footer()

    def action_next_screen(self):
        if not CURRENT_SCREEN.get():
            CURRENT_SCREEN.set(INSTALLED_SCREENS.get()[0])
        else:
            screens = INSTALLED_SCREENS.get()
            index = screens.index(CURRENT_SCREEN.get())
            count = len(screens)
            CURRENT_SCREEN.set(screens[(index + 1) % count])
        self.push_screen(CURRENT_SCREEN.get())

    def action_save(self):
        kayaku.save_all()
        self.bell()
        self.screen.mount(Notification("已保存更改"))


def mount_screens(__app):
    from kayaku.domain import _store

    installed = []
    quick_access.mount(Static("快速访问", classes="quick-access-panel"))
    for cls in _store.cls_domains.keys():
        __app.install_screen(KayakuScreen.from_model(cls), cls.__name__)
        quick_access.reg_screen(cls.__name__)
        installed.append(cls.__name__)
    if not installed:
        __app.install_screen(FallbackScreen(), "Fallback")
        quick_access.reg_screen("Fallback")
        installed.append("Fallback")
    INSTALLED_SCREENS.set(installed)


if __name__ == "__main__":
    app = EricTUI()
    # TUI_APP.set(app)
    app.run()
