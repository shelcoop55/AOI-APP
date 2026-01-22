import streamlit as st
import pandas as pd
from src.analysis.base import AnalysisTool
from src.plotting import create_defect_sunburst, create_defect_sankey

class InsightsTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Insights & Sankey"

    def render_sidebar(self):
        pass

    def render_main(self):
        selected_layer_nums = self.store.multi_layer_selection or self.store.layer_data.get_all_layer_nums()
        side_pills = st.session_state.get("analysis_side_pills", ["Front", "Back"])
        selected_verifs = st.session_state.get("multi_verification_selection", [])
        selected_quadrant = st.session_state.get("analysis_quadrant_selection", "All")

        # Collect Data (Optimized: No copying inside loop)
        dfs = []
        for layer_num in selected_layer_nums:
            sides = []
            if "Front" in side_pills: sides.append('F')
            if "Back" in side_pills: sides.append('B')

            for s in sides:
                layer = self.store.layer_data.get_layer(layer_num, s)
                if layer and not layer.data.empty:
                    # Append reference, concat will handle merging
                    dfs.append(layer.data)

        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)

            # 1. Filter Verif
            if 'Verification' in combined_df.columns and selected_verifs:
                 combined_df = combined_df[combined_df['Verification'].astype(str).isin(selected_verifs)]

            # 2. Filter Quadrant
            if selected_quadrant != "All" and 'QUADRANT' in combined_df.columns:
                 combined_df = combined_df[combined_df['QUADRANT'] == selected_quadrant]

            if not combined_df.empty:
                st.caption(f"Analyzing {len(combined_df)} defects from selected context.")

                c1, c2 = st.columns([2, 1], gap="medium")

                with c1:
                    # Chart Optimization: Limit slices handled in plotting function if needed
                    st.plotly_chart(create_defect_sunburst(combined_df), use_container_width=True)

                with c2:
                    st.markdown("##### Defect Statistics")
                    # Vectorized Calculation
                    total_defects = len(combined_df)

                    if 'DEFECT_TYPE' in combined_df.columns:
                        false_criteria = ['N', 'False', 'GE57']

                        # Aggregation
                        # Check if Verification column exists for false rate
                        has_verif = 'Verification' in combined_df.columns

                        if has_verif:
                            # Use vectorized string comparison or check
                            # Normalize verification for check
                            # Assuming loaded data is already normalized or consistent

                            # GroupBy
                            grouped = combined_df.groupby('DEFECT_TYPE', observed=True)

                            counts = grouped.size()

                            # False counts: sum boolean mask per group
                            # lambda is slow?
                            # Faster: Filter True/False first?
                            # mask = combined_df['Verification'].isin(false_criteria)
                            # false_df = combined_df[mask]
                            # false_counts = false_df.groupby('DEFECT_TYPE').size()
                            # But we need aligned index.

                            # Using agg with sum of boolean
                            # Convert verification to boolean "is_false" first
                            is_false = combined_df['Verification'].astype(str).isin(false_criteria)

                            # We can't assign to combined_df easily if it's a copy/view mix?
                            # It is a result of concat, so it's a new DF. Safe to modify.
                            combined_df['is_false'] = is_false

                            stats_df = combined_df.groupby('DEFECT_TYPE', observed=True).agg(
                                Count=('DEFECT_TYPE', 'count'),
                                FalseCount=('is_false', 'sum')
                            ).sort_values('Count', ascending=False)

                            stats_df['Percent'] = (stats_df['Count'] / total_defects) * 100
                            stats_df['False Rate'] = (stats_df['FalseCount'] / stats_df['Count']) * 100

                        else:
                            stats_df = combined_df['DEFECT_TYPE'].value_counts().to_frame(name='Count')
                            stats_df['Percent'] = (stats_df['Count'] / total_defects) * 100
                            stats_df['False Rate'] = 0.0

                        # Format for Display
                        # "Count (Pct%)"
                        display_data = []
                        for dtype, row in stats_df.iterrows():
                            # Filter out zero counts if any
                            if row['Count'] > 0:
                                display_data.append({
                                    "Defect Type": dtype,
                                    "Count": f"{int(row['Count'])} ({row['Percent']:.1f}%)",
                                    "False Rate": f"{row['False Rate']:.1f}%"
                                })

                        st.dataframe(
                            pd.DataFrame(display_data),
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Defect Type": st.column_config.TextColumn("Type"),
                                "Count": st.column_config.TextColumn("Count (% Total)"),
                                "False Rate": st.column_config.TextColumn("False Rate (N/False/GE57)")
                            }
                        )
                    else:
                        st.info("No defect type data available.")

                sankey = create_defect_sankey(combined_df)
                if sankey:
                    st.plotly_chart(sankey, use_container_width=True)
            else:
                st.warning("No data after filtering.")
        else:
            st.warning("No data selected.")
