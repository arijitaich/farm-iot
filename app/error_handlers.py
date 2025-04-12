from flask import Blueprint, render_template

error_bp = Blueprint('errors', __name__)

@error_bp.app_errorhandler(404)
def error_404(error):
    return render_template('404.html'), 404

@error_bp.app_errorhandler(500)
def error_500(error):
    return render_template('500.html'), 500
