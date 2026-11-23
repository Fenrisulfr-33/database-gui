# Expected Behavior

## Login screen

The login page requires 3 things to login.

1. Cluster
2. Username
3. Password

The expected behavior is to input a cluster, a username, and a password, then you hit login and if the values work you go to the dashboard page. If any value is incorrect you are prompted to check a the values. A remember me section should create a local .json file that stores a `username`, `password`, and `cluster` for a cluster. So they exist in a list where the cluster can also have a `name` that the user can assign to a cluster so they can access it easier.

Clarifications:

- Credentials are only saved after a **successful** login, so bad values are never stored.
- Picking a saved cluster by its `name` fills in the cluster, username, and password fields.
- The `name` is optional. The "Cluster name (optional)" box only shows while **Remember me** is checked.
- The **Remember me** checkbox is on the login screen (checked by default). If it is **unchecked**, nothing is added to the local `.json` file, even when the login works.
- Logging in again to the same cluster + username updates that saved entry (new password, and the new name if one was typed) instead of adding a duplicate.
- The saved-clusters dropdown only appears when the `.json` file has at least one entry.
- The file lives in the user's home folder at `~/.db_gui/saved_clusters.json`, outside the repo, so saved logins can't be committed by accident.

> **Security note (deferred):** For now the password is stored in plain text in the local `.json` file. Later, it should be encrypted or moved to the OS keyring instead of being saved in the file.

### Login flow

```mermaid
flowchart TD
    start(["App opens"]) --> login["Login screen"]
    login --> has_saved{"Saved clusters in<br/>local .json file?"}
    has_saved -- Yes --> pick{"Pick a saved<br/>cluster by name?"}
    pick -- Yes --> prefill["Fill in cluster, username,<br/>and password from saved entry"]
    pick -- No --> enter
    has_saved -- No --> enter["Enter cluster, username,<br/>and password"]
    prefill --> remember
    enter --> remember{"Remember me<br/>checked?"}
    remember -- Yes --> name["Cluster name box shown:<br/>optionally assign a name"]
    remember -- No --> submit
    name --> submit["Click Login"]
    submit --> valid{"Do the values work?"}
    valid -- No --> error["Prompt user to<br/>check the values"]
    error --> enter
    valid -- Yes --> save_check{"Remember me<br/>checked?"}
    save_check -- Yes --> exists{"Same cluster + username<br/>already saved?"}
    exists -- No --> save["Add name, cluster, username,<br/>and password to the list<br/>in the local .json file"]
    exists -- Yes --> update["Update that entry's password<br/>and name if a new one was typed"]
    save_check -- No --> skip["Don't touch the<br/>local .json file"]
    save --> dashboard(["Dashboard page"])
    update --> dashboard
    skip --> dashboard
```

#### Remember me storage

```mermaid
classDiagram
    class saved_clusters_json {
        list~saved_cluster~ clusters
    }
    class saved_cluster {
        string name
        string cluster
        string username
        string password
    }
    saved_clusters_json "1" --> "*" saved_cluster : contains
```

---

## Dashboard

The dashboard shows the all the clusters contents.

1. A list of the databases in said cluster.
2. 
