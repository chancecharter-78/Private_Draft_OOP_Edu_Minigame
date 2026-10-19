
import streamlit as st

from Controller import minigame, servers as controller


@st.dialog("Confirm Delete")
def confirm_delete_server(username, server_id, server_name):
    st.info(
        f"Would you like to delete **{server_name}**? \nQuestion sets are not affected."
    )
    cancel_col, delete_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key="cancel_delete_server"):
            controller.cancel_server_delete()
            st.rerun()
    with delete_col:
        if st.button("Decommission server", key="confirm_delete_server", type="primary",):
            if not controller.decommission_server(username, server_id, server_name):
                st.error("This server does not exist.")
                return
            st.rerun()


def render_server_list():
    st.title("Servers")
    notice = st.session_state.pop("server_repair_notice", "")
    if notice:
        st.success(notice)
    delete_notice = st.session_state.pop("server_delete_notice", "")
    if delete_notice:
        st.success(delete_notice)

    servers = controller.list_servers(st.session_state.username)
    if servers:
        columns = st.columns(3)
        for index, server in enumerate(servers):
            with columns[index % len(columns)]:
                st.button(
                    server["name"],
                    key=f"open_server_{server['id']}",
                    on_click=controller.open_server,
                    args=(server["id"],),
                    width="stretch",
                )
                if server["question_set_count"] == 0:
                    status = "Idle"
                    dot = "⚪"
                elif server["online"]:
                    status = "Online"
                    dot = "🟢"
                else:
                    status = "Offline"
                    dot = "🔴"
                st.caption(f"{dot} {status}")

    if st.button(
        "＋ Add server",
        key="add_server",
        type="primary",
        width="stretch",
    ):
        controller.add_server(st.session_state.username)
        st.rerun()


def render_server_menu():
    server_id = st.session_state.get("selected_server_id")
    if server_id is None:
        st.session_state.page = "Servers"
        st.rerun()
        return

    username = st.session_state.username
    server = controller.get_server_status(username, server_id)
    question_sets = controller.list_question_sets(username)
    names_by_id = {item["id"]: item["name"] for item in question_sets}
    selected_ids = controller.get_server_question_set_ids(username, server_id)

    if st.button("Return", key="back_to_servers"):
        controller.return_to_server_list()
        st.rerun()

    st.title(server["name"])

    notice = st.session_state.pop(f"server_name_notice_{server_id}", None)
    if notice:
        if notice[0] == "success":
            st.success(notice[1])
        else:
            st.error(notice[1])

    if server["question_set_count"] == 0:
        st.info("Status: Idle ⚪")
    elif server["online"]:
        st.success("Status: Online 🟢")
    else:
        st.warning("Status: Offline 🔴")

    st.subheader("Server Data")
    selection_key = f"server_question_sets_{server_id}"
    st.multiselect(
        "Configure server data",
        options=list(names_by_id),
        default=selected_ids,
        format_func=lambda set_id: names_by_id[set_id],
        key=selection_key,
        on_change=controller.save_server_question_sets_on_change,
        args=(username, server_id, selection_key),
    )

    if server["question_set_count"] > 0:
        if st.button(
            "Repair server" if not server["online"] else "Connect to server",
            key=f"start_server_{server_id}",
            type="primary",
        ):
            minigame.start_server_game(
                server_id,
                repairing=not server["online"],
            )
            st.rerun()

    with st.expander("Server Settings"):
        rename_open_key = f"rename_server_open_{server_id}"
        st.button(
            "Edit Server Name",
            key=f"open_rename_server_{server_id}",
            on_click=controller.toggle_server_rename,
            args=(server_id,),
        )

        name_key = f"server_name_{server_id}"
        if st.session_state.get(rename_open_key, False):
            st.text_input("Server name", value=server["name"], key=name_key)
            rename_columns = st.columns(2)
            with rename_columns[0]:
                st.button(
                    "Save",
                    key=f"rename_server_{server_id}",
                    type="primary",
                    on_click=controller.save_server_name_on_click,
                    args=(
                        username,
                        server_id,
                        name_key,
                        rename_open_key,
                    ),
                )
            with rename_columns[1]:
                st.button(
                    "Cancel",
                    key=f"cancel_rename_server_{server_id}",
                    on_click=controller.cancel_server_rename,
                    args=(server_id, name_key, rename_open_key),
                )

        if st.button(
            "Decommission Server",
            key=f"delete_server_{server_id}",
            type="secondary",
        ):
            controller.request_server_delete()

    if st.session_state.get("server_delete_confirmation_open", False):
        confirm_delete_server(
            username,
            server_id,
            server["name"],
        )


def main():
    if st.session_state.get("page") == "Server menu":
        render_server_menu()
    else:
        render_server_list()
