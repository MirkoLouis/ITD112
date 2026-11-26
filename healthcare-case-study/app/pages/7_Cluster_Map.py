"""Chart 4: hierarchical cluster map, R vs Python."""

import streamlit as st

from figure_compare import show_r_vs_python

st.title("Cluster Map")
st.write(
    "Hierarchical clustering of East Asia and Pacific economies "
    "(Euclidean distance, Ward linkage, z-scored input)."
)
show_r_vs_python("04_clustermap")
