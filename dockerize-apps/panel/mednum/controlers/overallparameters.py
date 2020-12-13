#!/usr/bin/env python
# coding: utf-8
import os
from pathlib import Path
import io
import geoviews as gv
import panel as pn
import param
from panel.widgets import Checkbox
from mednum.widgets import TreeViewCheckBox
from holoviews.element.tiles import StamenTerrain
from mednum.loaders import *
from pygal.style import Style
from mednum import tools
from mednum.config import *
import cProfile
import copy

import mednum as mind

gv.extension("bokeh")

class OverallParameters(param.Parameterized):
    localisation = param.String(default="Jegun", label="")
    score = param.Range(default=(0, 250), bounds=(0, 250),)

    tout_axes = param.Boolean(True, label="")
    interfaces_num = param.ListSelector(label="", default=list(CATEGORIES_INT_NUM_REV.keys()))
    infos_num = param.ListSelector(label="", default=list(CATEGORIES_X_INFOS_REV))
    comp_admin = param.ListSelector(label="", default=list(CATEGORIES_X_COMP_ADMIN_REV.keys()))
    comp_usage_num = param.ListSelector(label="", default=list(CATEGORIES_X_COMP_USAGE_REV.keys()))

    point_ref = param.Selector(
        default=SELECT[2], objects=SELECT, label="Point de référence",
    )

    niveau_observation = param.Selector(
        default=SELECT[2], objects=SELECT, label="Niveau d'observation",
    )

    niveau_details = param.Selector(
        default=SELECT[2], objects=SELECT, label="Niveau de détail",
    )

    donnees_infra = param.Action(
        lambda x: x, doc="""Données Infra-Communales""", precedence=0.7
    )

    file_name = param.String(
        default="Export_mednum.csv",
        doc="""
      The filename to save to.""",
    )
    edit_report = param.Action(
        lambda x: x.timestamps.append(dt.datetime.utcnow()),
        doc="""Editer un rapport""",
        precedence=0.7,
    )
    tiles = gv.tile_sources.StamenTerrain

    df_merged = param.DataFrame()
    df_score = param.DataFrame()

    def __init__(self, **params):
        super(OverallParameters, self).__init__(**params)
        interim_data, cont_iris, indice_frag = self.define_paths()

        # Merged
        output_data_path = interim_data / "add_geom_data_to_merged_data.trc.pqt"
        if output_data_path.exists():
            import geopandas as gpd

            self.df_merged = gpd.read_parquet(output_data_path)
        else:
            self.df_merged = add_geom_data_to_merged_data(
                iris_df(cont_iris), read_merged_data(indice_frag)
            )

        # Create multindex
        self.set_dataframes_indexes()
        self.set_dataframes_level()

        # Create widgets for indicators
        self.define_indices_params()

        # Define what is level 0 and level 1 to consider
        self.set_entity_levels()

        # What is selected in each level
        self.get_selected_indice_by_level()

        # Define define_searchable_element
        self.define_searchable_element()
         
        # Download
        self.download = pn.widgets.FileDownload(
            label="""Exporter les résultats""",
            filename=self.file_name,
            callback=self._download_callback,
        )

    def define_paths(self):
        data_path = Path("../data")

        if not data_path.exists():
            data_path = Path("./data")
        if not data_path.exists():
            data_path = Path("../../data")
        raw_data = data_path / "raw/"

        external_data = data_path / "external/"

        interim_data = data_path / "interim/"

        cont_iris = external_data / "france-geojson" / "contours-iris.geojson"

        indice_frag = processed_data / "MERGE_data_clean.csv"
        return interim_data, cont_iris, indice_frag

    def define_searchable_element(self):
        self.seachable_localisation = list(
            self.df_merged.index.get_level_values(self.level_0_column_names).unique()
        )

    def define_indices_params(self):
        """ 
        Create all indices parameters -> Will become a TreeCheckBox or Checkbox
        """
        self.g_params = []
        for k, widget_opts in TREEVIEW_CHECK_BOX.items():
            # Voir si description ne peut être passée
            widgets_params = self.create_checkbox_type_widget_params(widget_opts)

            self.g_params.append(pn.Param(self.param[k], widgets={k: widgets_params}))

    def _download_callback(self):
        """
            A FileDownload callback will return a file-like object which can be serialized
            and sent to the client.
            """
        self.file_name = "Export_%s.csv" % self.point_ref
        self.download.filename = self.file_name
        sio = io.StringIO()
        self.df_score.drop("geometry", axis=1).to_csv(sio, index=False)
        sio.seek(0)
        return sio

    def get_params(self):
        paramater_names = [par[0] for par in self.get_param_values()]
        return pn.Param(
            self.param,
            parameters=[par for par in paramater_names if par != "df_merged"],
        )

    def set_dataframes_level(self):
        real_name_level = []
        for col in self.df_merged.columns:
            if col in CATEGORIES_INDICES.keys():
                real_name_level.append((col, CATEGORIES_INDICES[col]))
            else:
                real_name_level.append((col, col))

        self.df_merged.columns = pd.MultiIndex.from_tuples(
            real_name_level, names=["variable", "nom"]
        )

    def set_dataframes_indexes(self):
        indexes = list(
            set(
                list(MAP_COL_WIDGETS["level_0"].values())
                + list(MAP_COL_WIDGETS["level_1"].values())
            )
        )
        self.df_merged.set_index(indexes, inplace=True)

    @pn.depends("localisation", "point_ref", "niveau_observation", watch=True)
    def set_entity_levels(self):
        """Set the entity levels and point values for this entity.
        """
        self.level_0_column, self.level_1_column, self.level_2_column = (
            MAP_COL_WIDGETS["level_0"]["index"],
            MAP_COL_WIDGETS["level_1"][self.point_ref],
            MAP_COL_WIDGETS["level_2"][self.niveau_observation],
        )
        self.level_0_column_names = MAP_COL_WIDGETS["level_0"]["names"]
        self.level_0_value = self.localisation

    @pn.depends(
        "tout_axes",
        "interfaces_num",
        "infos_num",
        "comp_admin",
        "comp_usage_num",
        watch=True,
    )
    def get_selected_indice_by_level(self):
        """get the indices of the selected column

        Args:
            self ([type]): [description]

        Returns:
            [type]: [description]
        """
        param_values = {k: v for k, v in self.param.get_param_values()}
        selected_col = []
        for axe, indices in param_values.items():
            if axe in TREEVIEW_CHECK_BOX.keys() and indices:
                for indice in indices:
                    try:
                        selected_col += [CATEGORIES_INDICES_REV[indice]]
                    except:
                        pass

        self.selected_indices_level_0 = list(set(selected_col))
        self.selected_indices_level_1 = list(set(selected_col))
        return self.selected_indices_level_0, self.selected_indices_level_1

    def create_checkbox_type_widget_params(self, widget_opts):
        """Create dict of widget type and checkbox params .

        Args:
            widget_opts ([type]): [description]

        Returns:
            [type]: [description]
        """
        if len(widget_opts.items()) > 3:
            select_options = [
                val["nom"]
                for opt, val in widget_opts.items()
                if opt not in ["nom", "desc"]
            ]
            descriptions = [
                val["desc"]
                for opt, val in widget_opts.items()
                if opt not in ["nom", "desc"]
            ]
            widget_type = TreeViewCheckBox
            widgets_params = {
                "type": widget_type,
                "select_options": select_options,
                "select_all": widget_opts["nom"],
                "desc": descriptions,
            }
        else:
            descriptions = widget_opts["desc"]
            widget_type = Checkbox
            widgets_params = {
                "name": widget_opts["nom"],
                "type": widget_type,
                "value": True,
                "desc": descriptions,
            }
        return widgets_params

    def set_real_name(df):
        real_name_level = []
        for col in df.columns:
            if col in CATEGORIES_INDICES.keys():
                real_name_level.append((col, CATEGORIES_INDICES[col]))
            else:
                real_name_level.append((col, col))

        return real_name_level

    def info_localisation(self):
        info_loc = {}
        index = self.df_merged.xs(
            self.localisation, level=self.level_0_column_names, drop_level=False
        ).index
        ids = index.unique().to_numpy()[0]
        names = index.names
        for k, v in zip(names, ids):
            info_loc[k] = v
        return info_loc

    def get_indices_properties(self):
        indices_properties = {}

        tree = copy.deepcopy(TREEVIEW_CHECK_BOX)
        for indic_dict in tree.values():
            indic_dict.pop("nom", None)
            indic_dict.pop("desc", None)
            indices_properties.update(indic_dict)
        return indices_properties
    
    
    @pn.depends(
        "localisation",
        "point_ref",
        "niveau_observation",
        "tout_axes",
        "interfaces_num",
        "infos_num",
        "comp_admin",
        "comp_usage_num",
        watch=True,
    )
    def score_calculation(self):
        indices_properties = self.get_indices_properties()
        selected_indices = self.selected_indices_level_0
        df = self.df_merged.droplevel("nom", axis=1)
        info_loc = self.info_localisation()
        if selected_indices != []:

            selected_indices_aggfunc = {
                k: indices_properties[k]["aggfunc"] for k in selected_indices
            }

            #
            map_info = [self.level_0_column_names]
            vdims = map_info + selected_indices

            # Aggregation selon la fonction specifié (mean, median)
            # au niveau level_1_column sur les indice selectionne selected_indices_aggfunc

            score_agg_niveau = df.groupby(self.level_1_column).agg(
                selected_indices_aggfunc
            )

            # Select level 25
            df_level_2 = df.xs(
                info_loc[self.level_2_column],
                level=self.level_2_column,
                drop_level=False,
            )
            # Division par l'aggregation sur la zone level_1_column (pondération)
            score_niveau = df_level_2[selected_indices].floordiv(score_agg_niveau) * 100

            # Dissolution (i.e. agregation geographique) au niveau de découpage souhaité level_0_column
            df = df_level_2.dissolve(
                by=[self.level_0_column, self.level_0_column_names],
                aggfunc=selected_indices_aggfunc,
            )

            # Score sur les indices merge sur l'index pour récupérer la geometry.
            # _BRUT : initial
            # _SCORE : Score de l'indice sur le découpage level_0_column divisé par la fonction d'aggragation au level_1_column
            scores = df.merge(
                score_niveau,
                on=[self.level_0_column, self.level_0_column_names],
                suffixes=("_BRUT", "_SCORE"),
            ).drop_duplicates()  # Drop duplicate pour supprimer les doublons (zone homogène)

            # Calcul des scores sur chaque axes et au total
            number_axes = 0
            for axe, indices in AXES_INDICES.items():
                selected_in_axes = [
                    k + "_SCORE" for k in indices.keys() if k in selected_indices
                ]
                if selected_in_axes != []:
                    scores.loc[:, axe] = scores[selected_in_axes].mean(axis=1).astype(int)
                    number_axes += 1
                else:
                    scores.loc[:, axe] = 0

            # Score total
            scores.loc[:, "tout_axes"] = scores[list(AXES_INDICES.keys())].sum(axis=1)
            if number_axes != 0:
                scores.loc[:, "tout_axes"] //= number_axes

            self.df_score = df.merge(
                scores, on=[self.level_0_column, self.level_0_column_names, "geometry"]
            ).drop_duplicates()  # Suppression des doublons sur les communes découpées en IRIS

        else:

            df = df.xs(
                info_loc[self.level_2_column],
                level=self.level_2_column,
                drop_level=False,
            ).dissolve(by=[self.level_0_column, self.level_0_column_names],)

            for axe, indices in AXES_INDICES.items():
                df.loc[:, axe] = 0
            df.loc[:, "tout_axes"] = 0

            self.df_score = df

