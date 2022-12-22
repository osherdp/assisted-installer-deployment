import abc


class LogsCollector(abc.ABC):
    @abc.abstractmethod()
    def logs_url_to_api(url):
        pass

    @abc.abstractmethod()
    def logs_url_to_ui(url):
        pass


class LocalDirLogsCollector(LogsCollector):
    def logs_url_to_api(url):
        """
        the log server has two formats for the url
        - URL for the UI  - http://assisted-logs-collector.usersys.redhat.com/#/2020-10-15_19:10:06_347ce6e8-bb4d-4751-825f-5e92e24da0d9/
        - URL for the API - http://assisted-logs-collector.usersys.redhat.com/files/2020-10-15_19:10:06_347ce6e8-bb4d-4751-825f-5e92e24da0d9/
        This function will return an API URL, regardless of which URL is supplied
        """
        return re.sub(r"(http://[^/]*/)#(/.*)", r"\1files\2", url)

    def logs_url_to_ui(url):
        """
        the log server has two formats for the url
        - URL for the UI  - http://assisted-logs-collector.usersys.redhat.com/#/2020-10-15_19:10:06_347ce6e8-bb4d-4751-825f-5e92e24da0d9/
        - URL for the API - http://assisted-logs-collector.usersys.redhat.com/files/2020-10-15_19:10:06_347ce6e8-bb4d-4751-825f-5e92e24da0d9/
        This function will return an UI URL, regardless of which URL is supplied
        """
        return re.sub(r"(http://[^/]*/)files(/.*)", r"\1#\2", url)


class MinioLogsCollector(LogsCollector):
    def logs_url_to_api(url):
        raise NotImplemented

    def logs_url_to_ui(url):
        raise NotImplemented
