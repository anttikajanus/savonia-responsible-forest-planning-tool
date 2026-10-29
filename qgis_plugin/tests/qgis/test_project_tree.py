"""Layer-tree reordering must survive queued GUI registry synchronization."""

import unittest


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsApplication, QgsProject, QgsVectorLayer


from savonia_responsible_forest_planning_tool.adapters import project_setup


class ProjectTreeTests(unittest.TestCase):
    def test_sorted_layers_survive_gui_event_processing(self):
        project = QgsProject()
        self.addCleanup(project.clear)
        references = project_setup.ensure_group_order(project, "fi")["references"]
        groups = project_setup._reference_groups(project, references, "fi")
        layers = []
        # Provider creation adds stands before habitats; setup sorts habitats first.
        for service_id in ("forest_centre_stand", "forest_centre_habitat"):
            layer = QgsVectorLayer("Polygon?crs=EPSG:3067", service_id, "memory")
            layer.setCustomProperty("savonia/service_id", service_id)
            project.addMapLayer(layer, False)
            groups["forest"].addLayer(layer)
            layers.append(layer)
        layer_ids = [layer.id() for layer in layers]
        project_setup._order_reference_layers(project, groups)
        QgsApplication.processEvents()
        QgsApplication.processEvents()
        self.assertEqual(set(project.mapLayers()), set(layer_ids))
        self.assertEqual([node.layerId() for node in groups["forest"].children()],
                         list(reversed(layer_ids)))

    def test_layer_moved_between_groups_keeps_identity_and_visibility(self):
        project = QgsProject()
        self.addCleanup(project.clear)
        layer = QgsVectorLayer("Polygon?crs=EPSG:3067", "habitats", "memory")
        project.addMapLayer(layer)
        node = project.layerTreeRoot().findLayer(layer.id())
        node.setItemVisibilityChecked(False)
        destination = project.layerTreeRoot().addGroup("forest")
        moved = project_setup._place_layer_in_group(project, destination, layer)
        QgsApplication.processEvents()
        QgsApplication.processEvents()
        self.assertIs(project.mapLayer(layer.id()), layer)
        self.assertEqual(destination.children(), [moved])
        self.assertFalse(moved.itemVisibilityChecked())

    def test_populated_group_moves_up_and_down_without_losing_children(self):
        for language in ("fi", "en"):
            with self.subTest(language=language):
                project = QgsProject()
                root = project.layerTreeRoot()
                group = root.addGroup("forest")
                root.addGroup("water")
                layer = QgsVectorLayer("Polygon?crs=EPSG:3067", "habitats", "memory")
                project.addMapLayer(layer, False)
                group.addLayer(layer).setItemVisibilityChecked(False)
                group.setExpanded(False)
                for index in (1, 0):
                    group = project_setup._move_tree_node(group, root, index)
                    QgsApplication.processEvents()
                    QgsApplication.processEvents()
                    self.assertIs(project.mapLayer(layer.id()), layer)
                    self.assertEqual(root.children()[index], group)
                    self.assertEqual(group.children()[0].layerId(), layer.id())
                    self.assertFalse(group.children()[0].itemVisibilityChecked())
                    self.assertFalse(group.isExpanded())
                project.clear()


if __name__ == "__main__":
    unittest.main()
