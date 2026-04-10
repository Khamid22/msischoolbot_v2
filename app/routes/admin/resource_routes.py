from flask import jsonify, request, session, url_for

from app.routes.admin.services.r2_storage_service import upload_resource_file, upload_thumbnail_file
from app.routes.admin.services.resources_service import (
    create_resource,
    create_resource_type,
    delete_resource,
    delete_resource_type,
    rename_resource_type,
)
from app.routes.admin.services.upload_progress_service import (
    begin_upload,
    complete_upload,
    fail_upload,
    normalize_upload_id,
    publish_upload_event,
)


def register_admin_resource_routes(
    router,
    *,
    render_admin_page,
):
    def is_xhr_request():
        requested_with = str(request.headers.get("X-Requested-With", "")).strip()
        return requested_with == "XMLHttpRequest"

    def xhr_success(message):
        return jsonify(
            {
                "ok": True,
                "message": message,
                "redirect_url": url_for("student.home", panel="resources", school="all"),
            }
        )

    def xhr_error(message, status_code=400):
        return (
            jsonify(
                {
                    "ok": False,
                    "message": message,
                }
            ),
            status_code,
        )

    @router.post("/admin/resources/types/add")
    def add_resource_type():
        resource_type_name = request.form.get("resource_type_name", "").strip()
        created, create_error = create_resource_type(resource_type_name)
        if not created:
            return (
                render_admin_page(
                    auth_error=create_error or "Unable to save resource type.",
                    admin_panel="resources",
                ),
                400,
            )

        return render_admin_page(
            admin_notice="Resource type saved.",
            admin_panel="resources",
        )

    @router.post("/admin/resources/types/<int:resource_type_id>/delete")
    def delete_resource_type_route(resource_type_id):
        deleted, delete_error = delete_resource_type(resource_type_id)
        if not deleted:
            return (
                render_admin_page(
                    auth_error=delete_error or "Unable to delete resource type.",
                    admin_panel="resources",
                ),
                400,
            )

        return render_admin_page(
            admin_notice="Resource type deleted.",
            admin_panel="resources",
        )

    @router.post("/admin/resources/types/<int:resource_type_id>/rename")
    def rename_resource_type_route(resource_type_id):
        resource_type_name = request.form.get("resource_type_name", "").strip()
        renamed, rename_error = rename_resource_type(resource_type_id, resource_type_name)
        if not renamed:
            return (
                render_admin_page(
                    auth_error=rename_error or "Unable to rename resource type.",
                    admin_panel="resources",
                ),
                400,
            )

        return render_admin_page(
            admin_notice="Resource type renamed.",
            admin_panel="resources",
        )

    @router.post("/admin/resources/add")
    def add_resource():
        upload_id = normalize_upload_id(request.form.get("upload_id", ""))
        if upload_id:
            begin_upload(upload_id)

        def publish_progress(
            *,
            percent,
            stage,
            message,
            eta_seconds=None,
        ):
            if not upload_id:
                return
            publish_upload_event(
                upload_id,
                percent=percent,
                stage=stage,
                message=message,
                eta_seconds=eta_seconds,
            )

        subject_name = request.form.get("resource_subject_name", "").strip()
        resource_type_id = request.form.get("resource_type_id", "").strip()
        folder_path = request.form.get("resource_folder_path", "").strip()
        title = request.form.get("resource_title", "").strip()
        description = request.form.get("resource_description", "").strip()
        resource_url = ""

        uploaded_resource = request.files.get("resource_file")
        uploaded_file_path = ""
        if uploaded_resource and str(uploaded_resource.filename or "").strip():
            publish_progress(
                percent=4.0,
                stage="upload_start",
                message="Starting resource file upload...",
            )
            uploaded_file_path, upload_error = upload_resource_file(
                uploaded_resource,
                subject_name=subject_name,
                folder_path=folder_path,
                progress_callback=publish_progress,
            )
            if upload_error:
                fail_upload(
                    upload_id,
                    message=upload_error,
                    percent=4.0,
                    stage="upload_error",
                )
                if is_xhr_request():
                    return xhr_error(upload_error)
                return (
                    render_admin_page(
                        auth_error=upload_error,
                        admin_panel="resources",
                    ),
                    400,
                )
        else:
            fail_upload(
                upload_id,
                message="Please upload a resource file.",
                percent=4.0,
                stage="upload_error",
            )
            if is_xhr_request():
                return xhr_error("Please upload a resource file.")
            return (
                render_admin_page(
                    auth_error="Please upload a resource file.",
                    admin_panel="resources",
                ),
                400,
            )

        uploaded_thumbnail = request.files.get("thumbnail_file")
        uploaded_thumbnail_path = ""
        if uploaded_thumbnail and str(uploaded_thumbnail.filename or "").strip():
            uploaded_thumbnail_path, thumb_error = upload_thumbnail_file(
                uploaded_thumbnail,
                subject_name=subject_name,
                folder_path=folder_path,
            )
            if thumb_error:
                fail_upload(
                    upload_id,
                    message=thumb_error,
                    percent=90.0,
                    stage="upload_error",
                )
                if is_xhr_request():
                    return xhr_error(thumb_error)
                return (
                    render_admin_page(
                        auth_error=thumb_error,
                        admin_panel="resources",
                    ),
                    400,
                )

        publish_progress(
            percent=98.0,
            stage="saving",
            message="Saving resource record...",
        )
        created, create_error = create_resource(
            subject_name=subject_name,
            resource_type_id=resource_type_id,
            folder_path=folder_path,
            title=title,
            description=description,
            resource_url=resource_url,
            resource_file_path=uploaded_file_path,
            thumbnail_file_path=uploaded_thumbnail_path,
            created_by_admin_id=session.get("admin_id"),
        )
        if not created:
            fail_upload(
                upload_id,
                message=create_error or "Unable to save resource.",
                percent=98.0,
                stage="save_error",
            )
            if is_xhr_request():
                return xhr_error(create_error or "Unable to save resource.")
            return (
                render_admin_page(
                    auth_error=create_error or "Unable to save resource.",
                    admin_panel="resources",
                ),
                400,
            )

        complete_upload(upload_id, message="Resource saved.")
        if is_xhr_request():
            return xhr_success("Resource saved.")
        return render_admin_page(
            admin_notice="Resource saved.",
            admin_panel="resources",
        )

    @router.post("/admin/resources/<int:resource_id>/delete")
    def delete_resource_route(resource_id):
        deleted, delete_error = delete_resource(resource_id)
        if not deleted:
            return (
                render_admin_page(
                    auth_error=delete_error or "Unable to delete resource.",
                    admin_panel="resources",
                ),
                400,
            )

        return render_admin_page(
            admin_notice="Resource deleted.",
            admin_panel="resources",
        )
