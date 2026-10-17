import streamlit as st


def show_header(
    title: str,
    subtitle: str,
    icon: str = "✦",
    badge: str = "CLINICAL INTELLIGENCE",
):
    """
    Display a reusable CareFlow page header.

    Args:
        title: Page title.
        subtitle: Short page description.
        icon: Icon displayed before the title.
        badge: Small label above the title.
    """

    st.markdown(
        f"""
        <div style="
            margin-bottom: 28px;
            padding-bottom: 20px;
            border-bottom: 1px solid #E2E8F0;
        ">
            <div style="
                display: inline-block;
                padding: 6px 11px;
                background: #CCFBF1;
                color: #115E59;
                border-radius: 20px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                margin-bottom: 14px;
            ">
                {badge}
            </div>

            <div style="
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            ">
                <span style="
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 46px;
                    height: 46px;
                    background: #DDF7F2;
                    border-radius: 14px;
                    font-size: 25px;
                ">
                    {icon}
                </span>

                <h1 style="
                    color: #102A43;
                    font-size: 32px;
                    font-weight: 800;
                    letter-spacing: -1px;
                    margin: 0;
                    line-height: 1.3;
                ">
                    {title}
                </h1>
            </div>

            <p style="
                color: #627D98;
                font-size: 14px;
                line-height: 1.7;
                margin-top: 12px;
                margin-bottom: 0;
                max-width: 850px;
            ">
                {subtitle}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )