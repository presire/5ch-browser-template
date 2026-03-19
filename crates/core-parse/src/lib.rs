#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubjectEntry {
    pub thread_key: String,
    pub title: String,
    pub response_count: u32,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DatEntry {
    pub name: String,
    pub mail: String,
    pub date_and_id: String,
    pub body: String,
}

pub fn parse_subject_line(line: &str) -> Option<SubjectEntry> {
    let (key, rest) = line.split_once(".dat<>")?;
    let (title, count_raw) = rest.rsplit_once(" (")?;
    let count = count_raw.strip_suffix(')')?.parse().ok()?;

    Some(SubjectEntry {
        thread_key: key.to_string(),
        title: title.to_string(),
        response_count: count,
    })
}

fn sanitize_dat_body(raw: &str) -> String {
    raw.replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<br />", "\n")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", "\"")
        .replace("&#39;", "'")
}

pub fn parse_dat_line(line: &str) -> Option<DatEntry> {
    let mut it = line.split("<>");
    let name = it.next()?.to_string();
    let mail = it.next()?.to_string();
    let date_and_id = it.next()?.to_string();
    let body_raw = it.next()?.to_string();
    let body = sanitize_dat_body(&body_raw);

    Some(DatEntry {
        name,
        mail,
        date_and_id,
        body,
    })
}

#[cfg(test)]
mod tests {
    use super::{parse_dat_line, parse_subject_line};

    #[test]
    fn parse_subject_line_works() {
        let line = "1234567890.dat<>thread title (345)";
        let got = parse_subject_line(line).expect("subject");
        assert_eq!(got.thread_key, "1234567890");
        assert_eq!(got.title, "thread title");
        assert_eq!(got.response_count, 345);
    }

    #[test]
    fn parse_dat_line_works() {
        let line = "name<>mail<>2026/03/19(木) 12:34:56.78 ID:abc<>hello<br>world<>";
        let got = parse_dat_line(line).expect("dat");
        assert_eq!(got.name, "name");
        assert_eq!(got.mail, "mail");
        assert_eq!(got.date_and_id, "2026/03/19(木) 12:34:56.78 ID:abc");
        assert_eq!(got.body, "hello\nworld");
    }
}
