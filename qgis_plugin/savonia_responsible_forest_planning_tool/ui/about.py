"""Localized identity and offline legal resources, independent of web access."""

from html import escape
from pathlib import Path

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextBrowser, QVBoxLayout

from .. import documentation
from ..i18n import tr


class ResponsibleForestPlanningAboutDialog(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.info = documentation.metadata(plugin.package_root)
        self.active_resource = None
        self.resize(680, 540)
        layout = QVBoxLayout(self)
        self.content = QTextBrowser(self)
        self.content.setOpenLinks(False)
        self.content.setOpenExternalLinks(False)
        self.content.anchorClicked.connect(self.open_link)
        layout.addWidget(self.content)
        self.legal_title = QLabel(self)
        self.legal_title.hide()
        layout.addWidget(self.legal_title)
        self.legal_text = QTextBrowser(self)
        self.legal_text.setOpenLinks(False)
        self.legal_text.hide()
        layout.addWidget(self.legal_text)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        self.buttons.rejected.connect(self.close)
        layout.addWidget(self.buttons)
        self.set_language(plugin.language)

    def set_language(self, language):
        self.language = language
        self.setWindowTitle(tr(language, "about_title"))
        self.buttons.button(QDialogButtonBox.StandardButton.Close).setText(tr(language, "close"))
        self.content.setAccessibleName(tr(language, "about"))
        self.legal_text.setAccessibleName(tr(language, "about_licences"))
        if self.active_resource is not None:
            self._refresh_legal_title()
        def link(key, label):
            return '<a href="savonia:{0}">{1}</a>'.format(key, escape(tr(language, label)))
        self.content.setHtml(
            "<h1>{name}</h1><p><strong>{prototype}</strong></p><p>{version}</p><p>{identity}</p>"
            "<p>{manual}<br>{online}<br>{repository}<br>{issues}</p>"
            "<h2>{licences}</h2><p>{own}<br>{notices}<br>{inventory}</p>"
            "<h2>{sources}</h2><p>{sources_text} {sources_link}</p>".format(
                name=escape(self.info.get("name[" + language + "]", self.info["name"])),
                prototype=escape(tr(language, "prototype_notice")),
                version=escape(tr(language, "about_version", version=self.info["version"])),
                identity=escape(tr(language, "about_identity")),
                manual=link("manual", "about_manual"),
                online=link("homepage", "about_online"),
                repository=link("repository", "about_repository"),
                issues=link("tracker", "about_issues"),
                licences=escape(tr(language, "about_licences")),
                own=link("licence", "about_own_licence"),
                notices=link("notices", "about_notices"),
                inventory=link("inventory", "about_inventory"),
                sources=escape(tr(language, "about_data_sources")),
                sources_text=escape(tr(language, "about_data_text")),
                sources_link=link("data-sources", "about_data_details")))

    def _refresh_legal_title(self):
        key = {"licence": "about_own_licence", "notices": "about_notices", "inventory": "about_inventory"}[self.active_resource]
        label = tr(self.language, key)
        self.legal_title.setText(label)
        self.legal_text.setAccessibleName(label)

    def open_link(self, url):
        key = url.path()
        if key in ("licence", "notices", "inventory"):
            try:
                resource = documentation.resource_url(key, self.plugin.package_root)
                path = Path(QUrl(resource).toLocalFile())
                try:
                    content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as error:
                    raise documentation.ResourceError(key, path, "unreadable") from error
            except documentation.ResourceError as error:
                self.plugin._documentation_error(error)
                return
            self.active_resource = key
            self._refresh_legal_title()
            self.legal_title.show()
            self.legal_text.setPlainText(content)
            self.legal_text.show()
            self.legal_text.setFocus()
        elif key in ("manual", "data-sources"):
            self.plugin.show_help(section="data-sources" if key == "data-sources" else "workflow")
        elif key in ("homepage", "repository", "tracker"):
            self.plugin.open_documentation_url(self.info.get(key, ""))
