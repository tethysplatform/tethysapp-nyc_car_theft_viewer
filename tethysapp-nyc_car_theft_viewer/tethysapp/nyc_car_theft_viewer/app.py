from tethys_sdk.base import TethysAppBase
from tethys_sdk.app_settings import CustomSetting

class NycCarTheftViewer(TethysAppBase):
    """
    Tethys app class for NYC Car Theft Stats Viewer.
    """

    name = 'NYC Car Theft Stats Viewer'
    description = ''
    package = 'nyc_car_theft_viewer'  # WARNING: Do not change this value
    index = 'home'
    icon = f'{package}/images/car-theft-icon.png'
    root_url = 'nyc-car-theft-viewer'
    color = '#5f27cd'
    tags = ''
    enable_feedback = False
    feedback_emails = []

    def custom_settings(self):
        custom_settings = (
            CustomSetting(
                name='plot_start_date',
                type=CustomSetting.TYPE_STRING,
                description='Start Date for Plot',
                required=True,
                default='09/30/2024'
            ),
            CustomSetting(
                name='plot_end_date',
                type=CustomSetting.TYPE_STRING,
                description='End Date for Plot',
                required=True,
                default='09/30/2024'
            ),
            CustomSetting(
                name='sort_type',
                type=CustomSetting.TYPE_STRING,
                description='Sort Type',
                required=True,
                default='month'
            )
        )

        return custom_settings

