"Stylesheets to customize Qt controls"

from pathlib import Path

assets_path = Path(__file__).parent.as_posix()

style_root_toolbutton = f"""
    QToolButton::right-arrow {{
        image: url({assets_path}/iconfinder_icon-ios7-arrow-right_211607.png);
    }}
    QToolButton::left-arrow {{
        image: url({assets_path}/iconfinder_icon-ios7-arrow-left_211689.png);
    }}
    QToolButton::menu-indicator {{
        image: none; /* https://stackoverflow.com/a/19993662 */
    }}
"""
